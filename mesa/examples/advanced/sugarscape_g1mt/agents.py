import math
import json 
import inspect
from mesa.discrete_space import CellAgent
from .contracts import Contract, ContractType, ContractStatus
from .investment import SimulatedAgent
from .database_logger import DatabaseLogger
from .utils import get_distance


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
            for contract in agent_contracts:
                if contract.contract_type == ContractType.TERM_LOAN and contract.due_step == current_sim_step:
                    if contract.creditor_id == self.unique_id:
                        sim_sugar += contract.total_repayment_amount
                    elif contract.debtor_id == self.unique_id:
                        sim_sugar -= contract.total_repayment_amount

            sim_sugar += expected_harvest
            sim_sugar *= (1 - self.spoilage_rate) # Sugar spoils
            sim_sugar -= metabolism
            if sim_sugar <= 0:
                return -1, True
        return sim_sugar, False

    def _calculate_utility_with_hypothetical_loan(self, investment_opp, loan: Contract | None):
        """Helper to simulate utility given a specific loan agreement (or None)."""
        horizon = self.get_capability('agent_look_ahead_horizon')
        
        sim_agent = SimulatedAgent(self)
        if loan:
            sim_agent.sugar += loan.principal
        
        return investment_opp.calculate_utility(sim_agent, horizon, hypothetical_loan=loan)

    def apply_spoilage(self):
        """Applies percentage-based spoilage to the agent's sugar."""
        if self.spoilage_rate > 0:
            self.sugar *= (1 - self.spoilage_rate)

    def _update_lifecycle_and_metabolize(self):
        """Handles end-of-step biological processes."""
        self.age += 1
        self.apply_spoilage()
        self.metabolize()
        self.maybe_die()

    def _process_active_investment(self):
        """Handles the logic for a step where the agent is busy investing."""
        self.investment_counter -= 1
        if self.investment_counter <= 0:
            self.current_investment.apply_reward_to(self)
            self.completed_investment_names.add(self.current_investment.name)
            self.is_investing = False
            self.current_investment = None

    def _evaluate_forage_action(self):
        """Calculates the utility of the 'FORAGE' action."""
        horizon = self.get_capability('agent_look_ahead_horizon')
        forage_utility, forage_death = self.simulate_forage_scenario(horizon)
        if forage_death:
            forage_utility = -1
        return (forage_utility, ("FORAGE", None))

    def _evaluate_investment_actions(self, forage_utility):
        """
        Evaluates all available investment opportunities (both self-funded and loan-funded).
        Yields a tuple (utility, action_data) for each viable option.
        """
        horizon = self.get_capability('agent_look_ahead_horizon')
        for opp in self.available_opportunities:
            if not opp.is_available(self):
                continue
            
            # Evaluate self-funded investment
            utility, is_death = opp.calculate_utility(self, horizon)
            if not is_death:
                yield (utility, ("INVEST", opp))
                continue

            # If self-funded leads to death, evaluate with a loan
            if self.lending_enabled:
                survival_cost = opp.cost["metabolism_during_investment"] * (opp.cost["duration"] + 1)
                shortfall = max(0, survival_cost - self.sugar)
                amount_needed = shortfall
                
                if amount_needed <= 0:
                    continue
                
                term = opp.cost["duration"] + 10
                draft_contract = Contract(
                    contract_type=ContractType.TERM_LOAN, creditor_id=-1,
                    debtor_id=self.unique_id, principal=amount_needed,
                    term_steps=term, issue_step=self.model.steps,
                    interest_schedule=[0]
                )
                
                utility_zero_interest, death_zero_interest = self._calculate_utility_with_hypothetical_loan(opp, draft_contract)
                if death_zero_interest:
                    continue

                reservation_amount = max(0, utility_zero_interest - forage_utility)
                if reservation_amount <= 0:
                    continue
                
                neighbors = [
                    agent
                    for cell in self.cell.get_neighborhood(self.lender_vision, include_center=False)
                    for agent in cell.agents
                    if isinstance(agent, Trader)
                ]
                self.random.shuffle(neighbors)

                for lender in neighbors:
                    lender_offer = lender.get_lending_offer(draft_contract, reservation_amount)
                    
                    if lender_offer is not None:
                        final_interest = (reservation_amount + lender_offer) / 2
                        hypothetical_loan = Contract(
                            contract_type=ContractType.TERM_LOAN, creditor_id=lender.unique_id,
                            debtor_id=self.unique_id, principal=amount_needed,
                            term_steps=term, issue_step=self.model.steps, interest_schedule=[final_interest]
                        )
                        final_utility, final_death = self._calculate_utility_with_hypothetical_loan(opp, hypothetical_loan)
                        
                        if not final_death:
                            yield (final_utility, ("INVEST_WITH_LOAN", opp, lender, amount_needed, final_interest))
                            # Found a lender, no need to ask others for this opportunity
                            break

    def _evaluate_and_choose_action(self):
        """The agent's 'brain'. It evaluates all options and returns the best one."""
        # The forage action serves as the baseline for comparison.
        forage_utility, forage_action_data = self._evaluate_forage_action()
        candidate_actions = [(forage_utility, forage_action_data)]

        if self.investments_enabled:
            # Pass forage utility to use in reservation price calculation.
            investment_options = self._evaluate_investment_actions(forage_utility)
            candidate_actions.extend(investment_options)
        
        candidate_actions.sort(key=lambda x: x[0], reverse=True)
        # The final action data is just the second element of the top-rated tuple
        return candidate_actions[0][1]

    def _execute_action(self, best_action_data):
        """The agent's 'hands'. It takes a chosen action and mutates state."""
        action_type = best_action_data[0]
        
        if action_type == "INVEST":
            _, investment_opp = best_action_data
            self.is_investing = True
            self.current_investment = investment_opp
            self.investment_counter = investment_opp.cost["duration"]
            self.set_capability("metabolism_sugar", investment_opp.cost["metabolism_during_investment"])
            self.available_opportunities.remove(investment_opp)

        elif action_type == "INVEST_WITH_LOAN":
            _, investment_opp, lender, amount_needed, final_interest = best_action_data
            
            term = investment_opp.cost["duration"] + 10
            final_contract = Contract(
                contract_type=ContractType.TERM_LOAN, creditor_id=lender.unique_id,
                debtor_id=self.unique_id, principal=amount_needed,
                term_steps=term, issue_step=self.model.steps,
                interest_schedule=[final_interest]
            )
            lender.sugar -= amount_needed
            self.sugar += amount_needed
            self.model.register_contract(final_contract)
            
            self.is_investing = True
            self.current_investment = investment_opp
            self.investment_counter = investment_opp.cost["duration"]
            self.set_capability("metabolism_sugar", investment_opp.cost["metabolism_during_investment"])
            self.available_opportunities.remove(investment_opp)

        else: # FORAGE
            self.move()
            self.eat()

    def step(self):
        """Main step logic for the agent."""
        self.process_contract_maturities()

        if self.is_investing:
            self._process_active_investment()
        else:
            best_action_data = self._evaluate_and_choose_action()
            self._execute_action(best_action_data)
            
        self._update_lifecycle_and_metabolize()


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