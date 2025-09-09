# sugarscape_g1mt/actions.py

from __future__ import annotations
import math
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Type, Tuple
import copy

from .contracts import Contract, ContractType, ContractStatus
from .utils import get_harvest_multiplier, get_metabolism_during_investment, get_capital_requirement
from .transactions import AssetType, TransferLeg, TransactionManifest

if TYPE_CHECKING:
    from .agents import Trader


# --- The SimulatedAgent class is now located in this file ---
class SimulatedAgent:
    """
    A lightweight, temporary agent for 'what-if' scenarios in utility calculations.
    It mimics a real agent's state and capabilities but avoids deep object copies.
    """
    def __init__(self, real_agent: Trader):
        self.real_agent = real_agent
        self.sugar = real_agent.sugar
        # Must be a deep copy so changes don't affect the real agent's dictionary
        self._capabilities = copy.deepcopy(real_agent._capabilities_DO_NOT_TOUCH)

        # --- New attribute to support dynamic investment simulation ---
        self.harvest_investment_level = real_agent.harvest_investment_level
        # Inherit the investment parameters directly from the real agent being simulated
        self.investment_params = real_agent.investment_params

        # --- New Simulated Portfolio ---
        # A deep copy of the agent's financial assets for isolated simulation.
        self.sim_portfolio = {} # {contract_id: contract_object_copy}
        owned_contract_ids = self.real_agent.model.contracts_by_agent.get(self.real_agent.unique_id, set())
        for cid in owned_contract_ids:
            c = self.real_agent.model.contracts_by_id.get(cid)
            # We only care about assets the agent owns and can transfer
            if c and c.status == ContractStatus.ACTIVE and c.is_transferable and c.creditor_id == self.real_agent.unique_id:
                self.sim_portfolio[cid] = copy.deepcopy(c)

    def get_total_deposit_principal(self) -> float:
        """
        Calculates the total value of all active demand deposits in the simulated portfolio.
        """
        total_principal = 0.0
        for contract in self.sim_portfolio.values():
            if (contract.contract_type == ContractType.DEMAND_DEPOSIT and
                contract.status == ContractStatus.ACTIVE):
                total_principal += contract.current_principal
        return total_principal


    def get_capability(self, key):
        return self._capabilities.get(key)
    
    def set_capability(self, key, value):
        self._capabilities[key] = value

    def get_current_harvest_multiplier(self) -> float:
        """Calculates harvest multiplier based on the simulated agent's investment level."""
        # This logic must mirror the real agent's helper method.
        return get_harvest_multiplier(
            level=self.harvest_investment_level,
            base_multiplier=self.investment_params.get("base_harvest_multiplier", 1.0),
            growth_factor=self.investment_params.get("benefit_growth_factor", 1.0)
        )

    def get_max_potential_harvest(self):
        """
        A simplified version of the real agent's perception, operating on the
        real agent's model and cell but using the simulated agent's capabilities.
        """
        vision = self.get_capability('vision')
        
        # This perception logic must mirror the real agent's find_best_foraging_cell
        neighboring_cells = [
            cell for cell in self.real_agent.cell.get_neighborhood(vision, include_center=True)
            if cell.is_empty or cell == self.real_agent.cell
        ]
        
        if not neighboring_cells:
            return 0

        max_harvest = 0
        for cell in neighboring_cells:
            harvest = self.get_potential_harvest(cell)
            if harvest > max_harvest:
                max_harvest = harvest
        
        return max_harvest

    def get_potential_harvest(self, cell):
        """Calculates harvest based on simulated capabilities."""
        # The old `harvest_multipliers` capability is replaced by a dynamic calculation.
        multiplier = self.get_current_harvest_multiplier()
        # Accesses the real model's static sugar distribution map
        # capacity = int(self.real_agent.model.sugar_distribution[cell.coordinate[1], cell.coordinate[0]])
        # Assuming a simple multiplier for now, not dependent on capacity.
        # This might need to be adjusted if the old capacity-based logic is still desired.
        return cell.sugar * multiplier


class Action(ABC):
    """
    Abstract Base Class for an action an agent can perform.
    An Action is a single, atomic "verb" in a Strategy's plan.
    It knows how to simulate its own impact and how to execute itself.
    """
    def __init__(self, agent: Trader):
        self.agent = agent

    @abstractmethod
    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
        """
        Simulates the action on a temporary 'SimulatedAgent'.
        This method MUST NOT modify the real agent's state.

        Args:
            sim_agent: A SimulatedAgent instance representing the agent's state
                       before this action.

        Returns:
            A tuple containing:
            - The final utility of the state after this action.
            - The new state of the SimulatedAgent after the action.
        """
        raise NotImplementedError

    @abstractmethod
    def execute(self):
        """
        Executes the action on the real agent, mutating its state.
        This should only be called after a strategy has been chosen.
        """
        raise NotImplementedError

    def get_enabler_action_types(self) -> List[Type[Action]]:
        """Returns a list of Action types that could potentially enable this action if it fails."""
        return []

    @classmethod
    def find_best_instance(cls, agent: Trader, **kwargs) -> Action | None:
        """
        A class method responsible for discovering the parameters for this action.
        The exact signature may vary for Pre- and Post-actions.
        Returns an instance of itself or None.
        """
        return None


class ForageAction(Action):
    """An action for moving to the best cell and harvesting sugar."""
    def __init__(self, agent: Trader):
        super().__init__(agent)
        # Pre-calculate the best cell to avoid re-calculating in simulate/execute
        self.target_cell = self.agent.find_best_foraging_cell()

    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
        """Simulates the sugar gained from foraging."""
        if not self.target_cell:
            harvest_amount = 0
        else:
            harvest_amount = sim_agent.get_potential_harvest(self.target_cell)
        
        sim_agent.sugar += harvest_amount

        # The total utility of this state is the agent's sugar.
        return sim_agent.sugar, sim_agent

    def execute(self):
        """Moves the agent and harvests the sugar."""
        if self.target_cell:
            # The real agent moves and eats
            self.agent.cell = self.target_cell
            self.agent.eat()


class InvestAction(Action):
    """An action for committing to a dynamic, level-based investment."""
    def __init__(self, agent: Trader, target_level: int, investment_params: dict):
        super().__init__(agent)
        self.target_level = target_level
        self.params = investment_params

        self.duration = self.params["investment_duration"]
        self.metabolism_during_investment = get_metabolism_during_investment(
            current_level=self.agent.harvest_investment_level,
            duration=self.duration,
            constant_k=self.params["constant_time_to_save"],
            base_multiplier=self.params["base_harvest_multiplier"],
            growth_factor=self.params["benefit_growth_factor"],
            reference_sugar=self.params["max_sugar_capacity_for_ref_income"],
            reference_metabolism=self.params["metabolism_normal_for_ref_income"]
        )
        self.capital_requirement = get_capital_requirement(
            metabolism_during_investment=self.metabolism_during_investment,
            duration=self.duration
        )
    
    def get_enabler_action_types(self) -> List[Type[Action]]:
        """An investment can be enabled by taking a loan."""
        return [TakeLoanAction]

    def _calculate_utility_core(self, agent: Trader, horizon: int, hypothetical_loan=None, starting_sim_agent=None) -> tuple[float, bool]:
        """
        Internal forecasting engine, formerly the logic of InvestmentOpportunity.calculate_utility.
        Calculates the forecasted utility (final sugar) of undertaking this investment.
        Returns a tuple of (utility, is_death).
        """
        # Determine the starting state for the simulation
        if starting_sim_agent:
            sim_agent = starting_sim_agent
        elif isinstance(agent, SimulatedAgent):
            sim_agent = agent
        else:
            sim_agent = SimulatedAgent(agent)
        
        # If a hypothetical loan is passed for a "what-if" scenario, add its principal
        if hypothetical_loan:
            sim_agent.sugar += hypothetical_loan.principal

        # New "Balance Sheet" affordability check
        if (sim_agent.sugar + sim_agent.get_total_deposit_principal()) < self.capital_requirement:
            return -1, True # Dies immediately if they can't afford the capital requirement

        # Get the agent's current contracts for the simulation
        agent_contract_ids = sim_agent.real_agent.model.contracts_by_agent.get(sim_agent.real_agent.unique_id, set())
        agent_contracts = [sim_agent.real_agent.model.contracts_by_id[cid] for cid in agent_contract_ids if sim_agent.real_agent.model.contracts_by_id[cid].status == ContractStatus.ACTIVE]

        # Also include the hypothetical loan in the contract list for cash flow projection
        if hypothetical_loan:
            agent_contracts.append(hypothetical_loan)

        # 1. Simulate survival during the investment period
        cost_duration = self.duration
        # The agent must survive the investment period AND the step it completes
        metabolism_cost_steps = cost_duration + 1
        
        for i in range(metabolism_cost_steps):
            current_sim_step = sim_agent.real_agent.model.steps + 1 + i
            # --- Ledger-Aware Cash Flow Projection ---
            for contract in agent_contracts:
                if contract.contract_type == ContractType.TERM_LOAN and contract.due_step == current_sim_step:
                    if contract.creditor_id == sim_agent.real_agent.unique_id:
                        sim_agent.sugar += contract.total_repayment_amount
                    elif contract.debtor_id == sim_agent.real_agent.unique_id:
                        sim_agent.sugar -= contract.total_repayment_amount
            # --- End Ledger-Aware ---

            sim_agent.sugar *= (1 - sim_agent.real_agent.spoilage_rate) # Sugar spoils
            sim_agent.sugar -= self.metabolism_during_investment
            
            # This simulation does not yet account for the "just-in-time" liquidation reflex.
            # It assumes the initial balance sheet is sufficient.
            if sim_agent.sugar <= 0:
                return -1, True # Agent dies during investment
        
        # 2. Apply the reward and forecast the rest of the horizon
        # The "reward" is the new investment level for the simulated agent
        sim_agent.harvest_investment_level = self.target_level
        
        remaining_horizon = horizon - metabolism_cost_steps
        if remaining_horizon > 0:
            expected_harvest = sim_agent.get_max_potential_harvest()
            metabolism_after_investment = sim_agent.real_agent.base_metabolism
            
            for i in range(remaining_horizon):
                current_sim_step = sim_agent.real_agent.model.steps + 1 + metabolism_cost_steps + i
                # --- Ledger-Aware Cash Flow Projection ---
                for contract in agent_contracts:
                    if contract.contract_type == ContractType.TERM_LOAN and contract.due_step == current_sim_step:
                        if contract.creditor_id == sim_agent.real_agent.unique_id:
                            sim_agent.sugar += contract.total_repayment_amount
                        elif contract.debtor_id == sim_agent.real_agent.unique_id:
                            sim_agent.sugar -= contract.total_repayment_amount
                # --- End Ledger-Aware ---

                sim_agent.sugar += expected_harvest
                sim_agent.sugar *= (1 - sim_agent.real_agent.spoilage_rate) # Sugar spoils
                sim_agent.sugar -= metabolism_after_investment
                if sim_agent.sugar <= 0:
                    return -1, True # Dies after investing, but before horizon ends
        
        return sim_agent.sugar, False

    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
        """
        Simulates the entire lifecycle of an investment to determine its
        long-term utility by calling the internal forecasting engine.
        """
        horizon = self.agent.get_capability("agent_look_ahead_horizon")
        final_sugar, is_death = self._calculate_utility_core(self.agent, horizon, starting_sim_agent=sim_agent)

        if is_death:
            return -math.inf, sim_agent
        
        sim_agent.sugar = final_sugar
        return final_sugar, sim_agent

    def calculate_utility_with_loan(self, agent: Trader, hypothetical_loan: Contract) -> tuple[float, bool]:
        """
        Helper to calculate utility of this investment with a hypothetical loan.
        This is used by the Strategy class to evaluate loan-funded scenarios.
        """
        horizon = agent.get_capability("agent_look_ahead_horizon")
        # Pass the hypothetical loan down to the core calculator.
        return self._calculate_utility_core(agent, horizon, hypothetical_loan=hypothetical_loan)

    def execute(self):
        """Sets the agent's state to 'investing'."""
        self.agent.is_investing = True
        self.agent.current_investment = self
        self.agent.investment_counter = self.duration
        self.agent.set_capability("metabolism_sugar", self.metabolism_during_investment)
        # The reward is applied upon completion of the investment, but for state tracking,
        # we update the agent's level now.
        self.agent.harvest_investment_level = self.target_level


class MakeDepositAction(Action):
    """A post-action for depositing surplus sugar to avoid spoilage."""
    def __init__(self, agent: Trader, depository: Trader, principal: float, interest_rate: float):
        super().__init__(agent)
        self.depository = depository
        self.principal = principal
        self.interest_rate = interest_rate

    @classmethod
    def find_best_instance(cls, agent: Trader, sim_agent_state: SimulatedAgent, **kwargs) -> Action | None:
        """Finds the best deposit opportunity for a given end-of-turn surplus."""
        # TEMPORARY DEBUG LOGGING
        log_data = {
            "agent_id": agent.unique_id,
            "step": agent.model.steps,
            "event": "make_deposit_evaluation",
            "initial_simulated_sugar": sim_agent_state.sugar,
            "metabolism": agent.get_capability('metabolism_sugar'),
            "deposit_buffer_horizon": agent.deposit_buffer_horizon,
            "neighbors_polled": []
        }
        
        # Use the deposit_buffer_horizon to determine "true" surplus
        metabolism = agent.get_capability('metabolism_sugar')
        buffer_sugar = metabolism * agent.deposit_buffer_horizon
        surplus = sim_agent_state.sugar - buffer_sugar
        log_data["calculated_surplus"] = surplus

        if surplus <= 0:
            log_data["reason_for_no_deal"] = "insufficient_surplus"
            # agent.model.db_logger.debug(agent.model.run_id, json.dumps(log_data))
            return None

        depositor_reservation_rate = -agent.spoilage_rate
        log_data["depositor_reservation_rate"] = depositor_reservation_rate
        
        best_offer = -math.inf
        best_depository = None

        # Poll neighbors for deposit offers
        neighbors = [n for cell in agent.cell.get_neighborhood(agent.lender_vision) for n in cell.agents if n is not agent]
        for neighbor in neighbors:
            offer = neighbor.get_deposit_offer(agent.unique_id, surplus)
            log_data["neighbors_polled"].append({"neighbor_id": neighbor.unique_id, "offer_received": offer})
            if offer is not None and offer > depositor_reservation_rate and offer > best_offer:
                best_offer = offer
                best_depository = neighbor
        
        if best_depository:
            final_rate = best_offer # The offer is the final rate
            log_data["final_decision"] = best_depository.unique_id
            # agent.model.db_logger.debug(agent.model.run_id, json.dumps(log_data))
            return cls(agent, best_depository, surplus, final_rate)
        
        log_data["reason_for_no_deal"] = "no_acceptable_offers"
        # agent.model.db_logger.debug(agent.model.run_id, json.dumps(log_data))
        return None

    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
        """
        Calculates the utility of making a deposit using a one-step lookahead,
        comparing the value of spoiled sugar vs. interest-gaining principal.
        """
        # 1. Calculate the agent's sugar level immediately after making the deposit.
        sugar_after_deposit = sim_agent.sugar - self.principal

        # 2. Estimate the value of the deposited principal after one step (it gains interest).
        deposit_value_next_step = self.principal * (1 + self.interest_rate)

        # 3. Estimate the value of the agent's remaining sugar after one step (it spoils).
        remaining_sugar_next_step = sugar_after_deposit * (1 - self.agent.spoilage_rate)

        # 4. The total utility is the agent's total expected wealth in the next step.
        utility = remaining_sugar_next_step + deposit_value_next_step

        # 5. The new state of the sim_agent reflects the immediate sugar loss.
        sim_agent.sugar = sugar_after_deposit
        
        return utility, sim_agent

    def execute(self):
        """Creates the DEMAND_DEPOSIT contract and transfers sugar."""
        deposit_contract = Contract(
            contract_type=ContractType.DEMAND_DEPOSIT,
            creditor_id=self.agent.unique_id,
            debtor_id=self.depository.unique_id,
            principal=self.principal,
            interest_schedule=[self.interest_rate] # Store rate here for reference
        )
        self.agent.sugar -= self.principal
        self.depository.sugar += self.principal
        self.agent.model.register_contract(deposit_contract)


class RaiseSugarFromDepositsAction(Action):
    """
    A sophisticated post-action that raises sugar to cover a deficit.
    It acts as a "factory", deciding on the best method (market sale or
    direct withdrawal) and encapsulating the plan for execution.
    """
    def __init__(self, agent: Trader, plan_details: dict):
        super().__init__(agent)
        self.plan_details = plan_details

    @classmethod
    def find_best_instance(cls, agent: Trader, sim_agent_state: SimulatedAgent, **kwargs) -> Action | None:
        """The "Planner". Finds the best way to cover a simulated sugar deficit."""
        metabolism = agent.get_capability('metabolism_sugar')
        deficit = max(0, metabolism - sim_agent_state.sugar)

        if deficit <= 0:
            return None
        
        # --- Priority 1: Attempt to Sell on the Open Market ---
        needed_sugar = deficit
        neighbors = [n for cell in agent.cell.get_neighborhood(agent.get_capability("vision")) for n in cell.agents if n.sugar > 0 and n is not agent]
        
        owned_cids = agent.model.contracts_by_agent.get(agent.unique_id, set())
        sim_deposits = [
            (cid, copy.deepcopy(agent.model.contracts_by_id[cid])) for cid in owned_cids
            if agent.model.contracts_by_id.get(cid) and
               agent.model.contracts_by_id[cid].contract_type == ContractType.DEMAND_DEPOSIT and
               agent.model.contracts_by_id[cid].creditor_id == agent.unique_id and
               agent.model.contracts_by_id[cid].status == ContractStatus.ACTIVE
        ]
        
        if sum(n.sugar for n in neighbors) >= needed_sugar and sum(c.current_principal for _, c in sim_deposits) >= needed_sugar:
            manifest = []
            is_split_trade_cache = {}
            sim_deposits.sort(key=lambda item: item[1].current_principal)
            
            temp_needed_sugar = needed_sugar
            while temp_needed_sugar > 1e-6:
                neighbors.sort(key=lambda n: n.sugar, reverse=True)
                neighbors = [n for n in neighbors if n.sugar > 1e-6]
                sim_deposits = [(cid, c) for cid, c in sim_deposits if c.current_principal > 1e-6]

                if not neighbors or not sim_deposits: break

                richest_neighbor = neighbors[0]
                smallest_deposit_id, smallest_deposit = sim_deposits[0]
                
                trade_amount = min(temp_needed_sugar, smallest_deposit.current_principal, richest_neighbor.sugar)
                if trade_amount <= 1e-6: break

                is_split = trade_amount < smallest_deposit.current_principal

                manifest.append(TransferLeg(AssetType.SUGAR, trade_amount, richest_neighbor.unique_id, agent.unique_id))
                deposit_leg = TransferLeg(AssetType.DEMAND_DEPOSIT, trade_amount, agent.unique_id, richest_neighbor.unique_id, asset_id=smallest_deposit_id)
                manifest.append(deposit_leg)
                is_split_trade_cache[(deposit_leg.asset_id, deposit_leg.amount, deposit_leg.dest_agent_id)] = is_split

                temp_needed_sugar -= trade_amount
                richest_neighbor.sugar -= trade_amount
                smallest_deposit.current_principal -= trade_amount
            
            sugar_raised = needed_sugar - temp_needed_sugar
            if manifest and math.isclose(sugar_raised, needed_sugar):
                plan_details = {"type": "SALE", "amount_to_raise": sugar_raised, "manifest": manifest, "is_split_cache": is_split_trade_cache}
                return cls(agent, plan_details)

        # --- Priority 2 (Fallback): Withdraw from Issuer ---
        owned_contract_ids = agent.model.contracts_by_agent.get(agent.unique_id, set())
        available_deposits = [
            (cid, agent.model.contracts_by_id.get(cid)) for cid in owned_contract_ids if 
            agent.model.contracts_by_id.get(cid) and 
            agent.model.contracts_by_id.get(cid).contract_type == ContractType.DEMAND_DEPOSIT and 
            agent.model.contracts_by_id.get(cid).creditor_id == agent.unique_id and 
            agent.model.contracts_by_id.get(cid).status == ContractStatus.ACTIVE
        ]
        available_deposits.sort(key=lambda item: item[1].current_principal)
        
        withdrawal_plan = []
        sugar_raised = 0
        for contract_id, contract in available_deposits:
            if sugar_raised >= deficit: break
            
            amount_to_call = contract.current_principal
            withdrawal_plan.append({"contract_id": contract_id, "contract_to_call": contract, "amount_to_call": amount_to_call})
            sugar_raised += amount_to_call
        
        if withdrawal_plan:
            plan_details = {"type": "WITHDRAWAL", "amount_to_raise": sugar_raised, "withdrawal_plan": withdrawal_plan}
            return cls(agent, plan_details)
        
        return None
    
    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
        """Simulates receiving the raised sugar."""
        amount_to_raise = self.plan_details.get("amount_to_raise", 0)
        sim_agent.sugar += amount_to_raise
        # The utility is simply the final sugar state, no complex lookahead needed
        return sim_agent.sugar, sim_agent

    def execute(self):
        """The "Executor". Reads the plan and dispatches to the correct logic."""
        plan_type = self.plan_details.get("type")

        if plan_type == "SALE":
            manifest = self.plan_details["manifest"]
            is_split_cache = self.plan_details["is_split_cache"]
            for leg in manifest:
                source_agent = self.agent.model.get_agent_by_id(leg.source_agent_id)
                dest_agent = self.agent.model.get_agent_by_id(leg.dest_agent_id)
                if not source_agent or not dest_agent: continue

                if leg.asset_type == AssetType.SUGAR:
                    source_agent.sugar -= leg.amount
                    dest_agent.sugar += leg.amount
                elif leg.asset_type == AssetType.DEMAND_DEPOSIT:
                    key = (leg.asset_id, leg.amount, leg.dest_agent_id)
                    is_split = is_split_cache.get(key, False)
                    original_contract = self.agent.model.contracts_by_id.get(leg.asset_id)
                    if not original_contract: continue
                    
                    if is_split:
                        remaining_principal = original_contract.current_principal - leg.amount
                        self.agent.model.split_contract(
                            original_contract_id=leg.asset_id,
                            split_definitions=[(remaining_principal, source_agent.unique_id), (leg.amount, dest_agent.unique_id)]
                        )
                    else:
                        self.agent.model.transfer_contract_ownership(contract_id=leg.asset_id, new_creditor_id=dest_agent.unique_id)
        
        elif plan_type == "WITHDRAWAL":
            for withdrawal in self.plan_details["withdrawal_plan"]:
                self.agent.model.process_deposit_call(
                    withdrawal["contract_id"],
                    withdrawal["contract_to_call"],
                    withdrawal["amount_to_call"]
                )


class TakeLoanAction(Action):
    """A pre-action for securing a loan to enable another action."""
    def __init__(self, agent: Trader, lender: Trader, principal: float, interest: float, term: int):
        super().__init__(agent)
        self.lender = lender
        self.principal = principal
        self.interest = interest
        self.term = term

    @classmethod
    def find_best_instance(cls, agent: Trader, core_action_to_enable: InvestAction, baseline_utility: float, **kwargs) -> TakeLoanAction | None:
        """
        Contains all logic for discovering and negotiating a loan.
        """
        # Now that logic is merged, core_action_to_enable is the InvestAction instance itself.
        opportunity = core_action_to_enable
        
        # Calculate how much sugar is needed
        survival_buffer = agent.get_capability("metabolism_sugar")
        
        # Calculate shortfall against the total balance sheet, not just sugar
        current_assets = agent.sugar + agent.get_total_deposit_principal()
        shortfall = max(0, opportunity.capital_requirement - current_assets + survival_buffer)

        amount_needed = shortfall
        if amount_needed <= 0:
            return None
        
        term = opportunity.duration + 10
        
        # 1. Simulate a zero-interest loan to find the best-case utility
        draft_contract = Contract(contract_type=ContractType.TERM_LOAN, creditor_id=-1, debtor_id=agent.unique_id, principal=amount_needed, interest_schedule=[0], term_steps=term)
        # Use the helper on the InvestAction instance to run the simulation
        utility_zero_interest, death_zero_interest = core_action_to_enable.calculate_utility_with_loan(agent, draft_contract)
        
        if death_zero_interest:
            return None

        # 2. Calculate borrower's reservation amount based on the baseline (forage) utility
        reservation_amount = max(0, utility_zero_interest - baseline_utility)
        if reservation_amount <= 0:
            return None

        # 3. Poll neighbors for offers
        neighbors = [
            neighbor
            for cell in agent.cell.get_neighborhood(agent.lender_vision, include_center=False)
            for neighbor in cell.agents
            if isinstance(neighbor, type(agent))
        ]
        agent.random.shuffle(neighbors)
        
        for lender in neighbors:
            lender_offer = lender.get_lending_offer(draft_contract, reservation_amount)
            if lender_offer is not None:
                # 4. If offer is good, create an instance of this Action class
                final_interest = (reservation_amount + lender_offer) / 2
                return cls(agent, lender, amount_needed, final_interest, term)
        
        return None

    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
        """Simulates receiving the loan principal."""
        sim_agent.sugar += self.principal
        return sim_agent.sugar, sim_agent

    def execute(self):
        """Creates the contract and transfers the sugar between real agents."""
        final_contract = Contract(
            contract_type=ContractType.TERM_LOAN,
            creditor_id=self.lender.unique_id,
            debtor_id=self.agent.unique_id,
            principal=self.principal,
            term_steps=self.term,
            issue_step=self.agent.model.steps,
            interest_schedule=[self.interest]
        )
        self.lender.sugar -= self.principal
        self.agent.sugar += self.principal
        self.agent.model.register_contract(final_contract)

class ContinueInvestmentAction(Action):
    """
    A placeholder 'do-nothing' action that represents the agent's state
    of continuing an existing investment.

    Its primary purpose is to serve as a baseline core action within the Strategy
    engine. This allows the agent to evaluate and execute reactive post-actions
    (like RaiseSugarFromDepositsAction) even while it is 'busy' investing.
    """
    def __init__(self, agent: Trader):
        super().__init__(agent)

    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
        """
        This action does not change the agent's state or produce utility on its own.
        It simply reflects the agent's current state for the Strategy engine.
        """
        return sim_agent.sugar, sim_agent

    def execute(self):
        """
        This action has no direct execution logic. The processing of the
        investment (e.g., decrementing the counter) is handled as a
        non-discretionary part of the agent's end-of-step lifecycle.
        """
        pass