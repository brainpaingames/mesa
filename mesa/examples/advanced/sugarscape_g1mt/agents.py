import math
import json 
import inspect
from mesa.discrete_space import CellAgent
from .contracts import Contract, ContractType, ContractStatus
from .investment import SimulatedAgent
from .database_logger import DatabaseLogger
from .utils import get_distance
from .actions import ForageAction, InvestAction, TakeLoanAction
from .strategies import Strategy


class Trader(CellAgent):
    """
    A trader agent that can choose between foraging and investing.
    - Has a metabolism of sugar.
    - Harvests sugar to survive.
    - Can invest sugar to permanently reduce metabolism.
    """

    def __init__(self, model, cell, sugar=0, metabolism_sugar=0, vision=0, max_age=0, expected_lifespan=0, agent_look_ahead_horizon=15, opportunities=None, investments_enabled=True, lending_enabled=True, lender_vision=7, lender_look_ahead_horizon=20, spoilage_rate=0.0):
        super().__init__(model)
        self.cell = cell
        # Sanitize all numeric inputs to standard Python types
        self.sugar = float(sugar)
        self.spoilage_rate = float(spoilage_rate)
        self.max_age = int(max_age)
        self.expected_lifespan = float(expected_lifespan)
        self.age = 0

        self._capabilities_DO_NOT_TOUCH = {
            "vision": int(vision),
            "metabolism_sugar": float(metabolism_sugar),
            "harvest_multipliers": [0.0, 1.0, 1.0, 1.0, 1.0],
            "agent_look_ahead_horizon": int(agent_look_ahead_horizon)
        }
        self.investments_enabled = investments_enabled
        self.lending_enabled = lending_enabled
        self.available_opportunities = opportunities.copy() if opportunities is not None else []
        self.completed_investment_names = set()
        self.is_investing = False
        self.investment_counter = 0
        self.current_investment = None
        self.lender_vision = int(lender_vision)
        self.lender_look_ahead_horizon = int(lender_look_ahead_horizon)

    def process_contract_maturities(self):
        """
        Handles accounting for any contracts that are due on the current step.
        This method is non-discretionary.
        """
        my_contract_ids = self.model.contracts_by_agent.get(self.unique_id, set()).copy()

        for contract_id in my_contract_ids:
            contract = self.model.contracts_by_id.get(contract_id)
            if not contract or contract.status != ContractStatus.ACTIVE:
                continue

            if contract.contract_type == ContractType.TERM_LOAN and contract.due_step == self.model.steps:
                if contract.debtor_id == self.unique_id:
                    amount_due = contract.total_repayment_amount
                    payment = min(self.sugar, amount_due)
                    
                    self.sugar -= payment
                    
                    creditor = self.model.get_agent_by_id(contract.creditor_id)
                    if creditor:
                        creditor.sugar += payment

                    if payment < amount_due:
                        self.model.update_contract_status(contract_id, ContractStatus.DEFAULTED)
                    else:
                        self.model.update_contract_status(contract_id, ContractStatus.REPAID)


    def get_lending_offer(self, draft_contract: Contract, borrower_reservation_amount: float) -> float | None:
        """
        The lender's passive evaluation of a loan proposal.
        Returns its own reservation amount (0.0) if acceptable, otherwise None.
        """
        lender_reservation_amount = 0.0

        if borrower_reservation_amount < lender_reservation_amount:
            return None
        
        borrower = self.model.get_agent_by_id(draft_contract.debtor_id)
        if borrower is None:
            return None

        borrower_cell_capacity = self.model.sugar_distribution[borrower.cell.coordinate]
        if borrower_cell_capacity < 3:
            return None

        sim_sugar = self.sugar
        worst_case_harvest = 0
        my_metabolism = self.get_capability("metabolism_sugar")
        for _ in range(self.lender_look_ahead_horizon):
            sim_sugar += worst_case_harvest
            # Lender must account for its own sugar spoiling
            sim_sugar *= (1 - self.spoilage_rate)
            sim_sugar -= my_metabolism
        surplus_sugar = max(0, sim_sugar)

        if draft_contract.principal > surplus_sugar:
            return None

        return lender_reservation_amount

    def get_capability(self, key):
        """Public getter for a capability."""
        return self._capabilities_DO_NOT_TOUCH[key]

    def set_capability(self, key, value):
        """Public setter for a capability with built-in, verbose JSON logging."""
        caller_frame = inspect.stack()[1]
        caller_function = caller_frame.function
        caller_filename = caller_frame.filename.split('\\')[-1]
        
        try:
            caller_class = caller_frame.frame.f_locals['self'].__class__.__name__
        except (KeyError, AttributeError):
            caller_class = "N/A"

        old_value = self._capabilities_DO_NOT_TOUCH.get(key)
        if hasattr(old_value, 'item'): old_value = old_value.item()
        if hasattr(value, 'item'): value = value.item()



        self._capabilities_DO_NOT_TOUCH[key] = value

    def get_reportable_attributes(self):
        """Returns a dictionary of agent attributes for database logging."""
        pos_x, pos_y = (self.cell.coordinate[0], self.cell.coordinate[1]) if self.cell is not None else (None, None)
        return {
            "pos_x": pos_x,
            "pos_y": pos_y,
            "sugar": float(self.sugar),
            "spoilage_rate": float(self.spoilage_rate),
            "metabolism": float(self.get_capability("metabolism_sugar")),
            "vision": int(self.get_capability("vision")),
            "age": float(self.age),
            "max_age": int(self.max_age),
            "expected_lifespan": float(self.expected_lifespan),
            "is_investing": int(self.is_investing),
            "agent_look_ahead_horizon": int(self.get_capability("agent_look_ahead_horizon")),
            "completed_investments": json.dumps(list(self.completed_investment_names)),
        }

    def calculate_welfare(self, sugar):
        """
        Helper function for self.move().
        In this simplified model, welfare is simply the amount of sugar.
        """
        return sugar

    def is_starved(self):
        """
        Helper function for self.maybe_die().
        """
        return self.sugar <= 0

    def get_potential_harvest(self, cell):
        """Calculates the potential sugar harvest from a given cell based on current capabilities."""
        multipliers = self.get_capability("harvest_multipliers")
        capacity = int(self.model.sugar_distribution[cell.coordinate[0], cell.coordinate[1]])
        return cell.sugar * multipliers[capacity]

    def find_best_foraging_cell(self):
        """Finds the best cell to forage from in the agent's vision, including its current cell."""
        vision = self.get_capability('vision')

  
            
        neighboring_cells = [
            cell
            for cell in self.cell.get_neighborhood(vision, include_center=True)
            if cell.is_empty or cell == self.cell
        ]
        
        if not neighboring_cells:
            return None

        welfares = [
            self.calculate_welfare(self.sugar + self.get_potential_harvest(cell))
            for cell in neighboring_cells
        ]

        max_welfare = max(welfares)
        candidate_indices = [
            i for i, w in enumerate(welfares) if math.isclose(w, max_welfare)
        ]
        candidates = [neighboring_cells[i] for i in candidate_indices]

        min_dist = min(get_distance(self.cell, cell) for cell in candidates)

        final_candidates = [
            cell
            for cell in candidates
            if math.isclose(get_distance(self.cell, cell), min_dist, rel_tol=1e-2)
        ]

        return self.random.choice(final_candidates)
    
    def eat(self):
        """
        Agent harvests sugar from its current cell.
        """
        self.sugar += self.get_potential_harvest(self.cell)
        self.cell.sugar = 0

    def apply_spoilage(self):
        """Applies percentage-based spoilage to the agent's sugar."""
        if self.spoilage_rate > 0:
            self.sugar *= (1 - self.spoilage_rate)

    def _update_lifecycle_and_metabolize(self):
        """
        Handles the final, non-discretionary part of the agent's step,
        including aging, spoilage, metabolism, and checking for death.
        """
        self.age += 1
        self.apply_spoilage()
        self.metabolize()
        self.maybe_die()

    def _process_active_investment(self):
        """
        Handles the logic for a step where the agent is busy investing.
        This involves decrementing the counter and applying the reward on completion.
        """
        self.investment_counter -= 1
        if self.investment_counter <= 0:
            self.current_investment.apply_reward_to(self)
            self.completed_investment_names.add(self.current_investment.name)
            self.is_investing = False
            self.current_investment = None

    def _find_best_plan(self):
        """
        The agent's new "brain". It creates a "tournament" of possible strategies,
        evaluates them, and returns the action plan of the winner.
        """
        # 1. Assemble the "tool-kit" of available action types based on flags
        pre_action_kit = []
        if self.lending_enabled:
            pre_action_kit.append(TakeLoanAction)
        
        post_action_kit = [] # Ready for future actions like deposits

        # 2. Establish the baseline strategy (Foraging)
        forage_strategy = Strategy(ForageAction(self), pre_action_kit, post_action_kit)
        baseline_utility = forage_strategy.evaluate(self)
        
        candidate_strategies = [forage_strategy]

        # 3. Generate and evaluate investment strategies if enabled
        if self.investments_enabled:
            for opp in self.available_opportunities:
                if opp.is_available(self):
                    # Pass the assembled tool-kit to each investment strategy
                    invest_strategy = Strategy(InvestAction(self, opp), pre_action_kit, post_action_kit)
                    invest_strategy.evaluate(self, baseline_utility=baseline_utility)
                    candidate_strategies.append(invest_strategy)

        if not candidate_strategies:
            return []
        
        # 4. Find the winning strategy from the fully evaluated candidates
        best_strategy = max(candidate_strategies, key=lambda s: s.utility)

        # Return the winning plan (a list of Action objects)
        return best_strategy.get_action_plan()

    def step(self):
        """
        The main entry point for the agent's turn. It follows a strict
        sequence of operations: settle contracts, decide and act, and finally
        update biological state.
        """
        self.process_contract_maturities()

        if self.is_investing:
            self._process_active_investment()
        else:
            # The new, cleaner decision-making process
            best_plan = self._find_best_plan()
            
            # Execute the sequence of actions in the winning plan
            if best_plan:
                for action in best_plan:
                    action.execute()
            
        self._update_lifecycle_and_metabolize()

    def metabolize(self):
        """Agent consumes sugar for metabolism."""
        self.sugar -= self.get_capability('metabolism_sugar')
        
    def maybe_die(self):
        """
        Function to remove agents who have consumed all their sugar.
        """
        if self.is_starved() or self.age >= self.max_age:
            self.remove()