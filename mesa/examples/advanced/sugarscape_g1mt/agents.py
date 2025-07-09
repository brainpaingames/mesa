import math
import json 
import inspect
from mesa.discrete_space import CellAgent
from .contracts import Contract, ContractType, ContractStatus
from .investment import SimulatedAgent

def get_distance(cell_1, cell_2):
    """
    Calculate the Euclidean distance between two positions.
    Used in Trader.move()
    """
    x1, y1 = cell_1.coordinate
    x2, y2 = cell_2.coordinate
    dx = x1 - x2
    dy = y1 - y2
    return math.sqrt(dx**2 + dy**2)


class Trader(CellAgent):
    """
    A trader agent that can choose between foraging and investing.
    - Has a metabolism of sugar.
    - Harvests sugar to survive.
    - Can invest sugar to permanently reduce metabolism.
    """

    def __init__(self, model, cell, sugar=0, metabolism_sugar=0, vision=0, max_age=0, expected_lifespan=0, agent_look_ahead_horizon=15, opportunities=None, investments_enabled=True, lender_vision=7, lender_look_ahead_horizon=20):
        super().__init__(model)
        self.cell = cell
        # Sanitize all numeric inputs to standard Python types
        self.sugar = float(sugar)
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
                    
                    # Find the creditor to transfer funds
                    creditor = self.model.schedule.agents[contract.creditor_id]
                    creditor.sugar += payment

                    if payment < amount_due:
                        self.model.update_contract_status(contract_id, ContractStatus.DEFAULTED)
                    else:
                        self.model.update_contract_status(contract_id, ContractStatus.REPAID)

    def accept_loan_proposal(self, draft_contract: Contract, borrower_reservation_amount: float) -> bool:
        """
        The lender's evaluation of a loan proposal. If accepted, the lender finalizes
        the deal and registers the contract.
        Returns True if the deal was made, False otherwise.
        """
        # --- Lender's Reservation Rate ---
        lender_reservation_amount = 0.0 # V1: Lenders are willing to lend at zero interest

        if borrower_reservation_amount < lender_reservation_amount:
            return False # Borrower's max offer is less than my minimum demand

        # --- Due Diligence on Borrower ---
        borrower = self.model.schedule.agents[draft_contract.debtor_id]
        borrower_cell_capacity = self.model.sugar_distribution[borrower.cell.coordinate]
        if borrower_cell_capacity < 3:
            return False # Borrower is in a poor area, too risky

        # --- Surplus Calculation on Self (Lender) ---
        sim_sugar = self.sugar
        worst_case_harvest = 0
        my_metabolism = self.get_capability("metabolism_sugar")
        for _ in range(self.lender_look_ahead_horizon):
            sim_sugar += worst_case_harvest
            sim_sugar -= my_metabolism
        surplus_sugar = max(0, sim_sugar)

        if draft_contract.principal > surplus_sugar:
            return False # I cannot afford to lend this much

        # --- Finalize and Execute Deal ---
        final_interest = (borrower_reservation_amount + lender_reservation_amount) / 2
        
        draft_contract.interest_schedule = [final_interest]
        draft_contract.creditor_id = self.unique_id

        # Transfer funds
        self.sugar -= draft_contract.principal
        borrower.sugar += draft_contract.principal

        # Register the now-active contract
        self.model.register_contract(draft_contract)
        
        return True

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
        # Convert numpy types to native Python types for JSON serialization
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

    def get_max_potential_harvest(self):
        """Helper to perceive the best foraging spot in the current vision for forecasting."""
        best_cell = self.find_best_foraging_cell()
        return self.get_potential_harvest(best_cell) if best_cell else 0

    def simulate_forage_scenario(self, horizon):
        """Simulates future sugar if agent only forages."""
        sim_sugar = self.sugar
        expected_harvest = self.get_max_potential_harvest()
        metabolism = self.get_capability("metabolism_sugar")
        
        agent_contract_ids = self.model.contracts_by_agent.get(self.unique_id, set())
        agent_contracts = [self.model.contracts_by_id[cid] for cid in agent_contract_ids if self.model.contracts_by_id[cid].status == ContractStatus.ACTIVE]

        for i in range(horizon):
            current_sim_step = self.model.steps + 1 + i
            # --- Ledger-Aware Cash Flow Projection ---
            for contract in agent_contracts:
                if contract.contract_type == ContractType.TERM_LOAN and contract.due_step == current_sim_step:
                    if contract.creditor_id == self.unique_id:
                        sim_sugar += contract.total_repayment_amount
                    elif contract.debtor_id == self.unique_id:
                        sim_sugar -= contract.total_repayment_amount
            # --- End Ledger-Aware ---

            sim_sugar += expected_harvest
            sim_sugar -= metabolism
            if sim_sugar <= 0:
                return -1, True
        return sim_sugar, False

    def step(self):
        """Main step logic for the agent."""
        if self.is_investing:
            self.investment_counter -= 1
            if self.investment_counter <= 0:
                self.current_investment.apply_reward_to(self)
                self.completed_investment_names.add(self.current_investment.name)
                self.is_investing = False
                self.current_investment = None
        else:
            # --- Agent Decision Logic ---
            horizon = self.get_capability('agent_look_ahead_horizon')

            # 1. Evaluate the status quo (foraging)
            forage_utility, forage_death = self.simulate_forage_scenario(horizon)
            
            best_utility = forage_utility
            best_is_death = forage_death
            chosen_action = ("FORAGE", None)

            if self.investments_enabled:
                # 2. Evaluate all available investment opportunities
                for opp in self.available_opportunities:
                    if opp.is_available(self):
                        invest_utility, invest_death = opp.calculate_utility(self, horizon)
                        
                        # Prioritize survival, then highest utility
                        if best_is_death and not invest_death:
                            best_utility = invest_utility
                            best_is_death = invest_death
                            chosen_action = ("INVEST", opp)
                        elif not best_is_death and not invest_death:
                            if invest_utility > best_utility:
                                best_utility = invest_utility
                                chosen_action = ("INVEST", opp)

            # 3. Execute the chosen action
            action_type, investment_opp = chosen_action
            if action_type == "INVEST":
                self.is_investing = True
                self.current_investment = investment_opp
                self.investment_counter = investment_opp.cost["duration"]
                self.set_capability("metabolism_sugar", investment_opp.cost["metabolism_during_investment"])
                self.available_opportunities.remove(investment_opp)
            else: # FORAGE
                self.move()
                self.eat()

        self.age += 1
        self.metabolize()
        self.maybe_die()

    def move(self):
        """Moves the agent to the best foraging cell in its vision."""
        best_cell = self.find_best_foraging_cell()
        if best_cell:
            self.cell = best_cell

    def eat(self):
        """
        Agent harvests sugar from its current cell.
        """
        self.sugar += self.get_potential_harvest(self.cell)
        self.cell.sugar = 0

    def metabolize(self):
        """Agent consumes sugar for metabolism."""
        self.sugar -= self.get_capability('metabolism_sugar')
        
    def maybe_die(self):
        """
        Function to remove agents who have consumed all their sugar.
        """
        if self.is_starved() or self.age >= self.max_age:
            self.remove()