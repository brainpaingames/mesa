# sugarscape_g1mt/actions.py

from __future__ import annotations
import math
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Type, Tuple
import copy

from .contracts import Contract, ContractType, ContractStatus
from .investment import SimulatedAgent
from .transactions import AssetType, TransferLeg, TransactionManifest

if TYPE_CHECKING:
    from .agents import Trader
    from .investment import InvestmentOpportunity

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
            harvest_amount = self.agent.get_potential_harvest(self.target_cell)
        
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
    """An action for committing to an investment."""
    def __init__(self, agent: Trader, opportunity: InvestmentOpportunity):
        super().__init__(agent)
        self.opportunity = opportunity

    def get_enabler_action_types(self) -> List[Type[Action]]:
        """An investment can be enabled by taking a loan or converting assets."""
        return [TakeLoanAction, ConvertDepositToSugarAction]

    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
        """
        Simulates the entire lifecycle of an investment to determine its
        long-term utility.
        """
        horizon = self.agent.get_capability("agent_look_ahead_horizon")
        final_sugar, is_death = self.opportunity.calculate_utility(self.agent, horizon, starting_sim_agent=sim_agent)

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
        # Pass the hypothetical loan down to the opportunity's calculator, which knows how to handle it.
        return self.opportunity.calculate_utility(agent, horizon, hypothetical_loan=hypothetical_loan)

    def execute(self):
        """Sets the agent's state to 'investing'."""
        self.agent.is_investing = True
        self.agent.current_investment = self.opportunity
        self.agent.investment_counter = self.opportunity.cost["duration"]
        self.agent.set_capability("metabolism_sugar", self.opportunity.cost["metabolism_during_investment"])
        if self.opportunity in self.agent.available_opportunities:
             self.agent.available_opportunities.remove(self.opportunity)


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


class CallDepositAction(Action):
    """A post-action for calling a deposit to cover a sugar deficit."""
    def __init__(self, agent: Trader, contract_id: int, contract_to_call: Contract, amount_to_call: float):
        super().__init__(agent)
        self.contract_id = contract_id
        self.contract_to_call = contract_to_call
        self.amount_to_call = amount_to_call

    @classmethod
    def find_best_instance(cls, agent: Trader, sim_agent_state: SimulatedAgent, **kwargs) -> Action | None:
        """Finds a deposit to call if the agent is in a simulated deficit."""
        metabolism = agent.get_capability('metabolism_sugar')
        deficit = max(0, metabolism - sim_agent_state.sugar)

        if deficit <= 0:
            return None
        
        # Correctly get the agent's contract IDs from the model
        owned_contract_ids = agent.model.contracts_by_agent.get(agent.unique_id, set())
        
        for contract_id in owned_contract_ids:
            contract = agent.model.contracts_by_id.get(contract_id)
            if (contract and
                contract.contract_type == ContractType.DEMAND_DEPOSIT and
                contract.creditor_id == agent.unique_id and
                contract.status == ContractStatus.ACTIVE and
                contract.current_principal > 0):
                
                # Simple strategy: call the first suitable one found
                amount_to_call = min(deficit, contract.current_principal)
                return cls(agent, contract_id, contract, amount_to_call)
        
        return None
    
    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
        """Simulates receiving the called sugar."""
        sim_agent.sugar += self.amount_to_call
        return sim_agent.sugar, sim_agent

    def execute(self):
        """Executes the call via the model's authoritative method."""
        # Now we have the contract_id to pass to the model
        self.agent.model.process_deposit_call(self.contract_id, self.contract_to_call, self.amount_to_call)


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
        opportunity = core_action_to_enable.opportunity
        
        # Calculate how much sugar is needed
        survival_cost = opportunity.cost["metabolism_during_investment"] * (opportunity.cost["duration"] + 1)
        shortfall = max(0, survival_cost - agent.sugar)
        amount_needed = shortfall
        if amount_needed <= 0:
            return None
        
        term = opportunity.cost["duration"] + 10
        
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


class ConvertDepositToSugarAction(Action):
    """
    A self-contained action for liquidating deposits to generate sugar.
    Its planner uses the "No-Split-First" greedy heuristic.
    """
    def __init__(self, agent: Trader, manifest: TransactionManifest, sugar_to_generate: float):
        super().__init__(agent)
        self.manifest = manifest
        self.sugar_to_generate = sugar_to_generate
        self.is_split_trade = {} # Cache for execution logic

    @classmethod
    def find_best_instance(cls, agent: Trader, core_action_to_enable: Action, **kwargs) -> Action | None:
        """The 'Planner'. Builds a transaction manifest to cover a sugar shortfall."""
        if not isinstance(core_action_to_enable, InvestAction):
            return None
        
        opportunity = core_action_to_enable.opportunity
        cost_of_survival = opportunity.cost["metabolism_during_investment"] * (opportunity.cost["duration"] + 1)
        shortfall = max(0, cost_of_survival - agent.sugar)

        if shortfall <= 0:
            return None

        # --- 1. Pre-computation & Sanity Checks ---
        neighbors = [n for cell in agent.cell.get_neighborhood(agent.vision) for n in cell.agents if n.sugar > 0]
        total_neighbor_sugar = sum(n.sugar for n in neighbors)

        owned_cids = agent.model.contracts_by_agent.get(agent.unique_id, set())
        deposits = [
            (cid, copy.copy(agent.model.contracts_by_id[cid])) for cid in owned_cids
            if agent.model.contracts_by_id.get(cid) and
               agent.model.contracts_by_id[cid].contract_type == ContractType.DEMAND_DEPOSIT and
               agent.model.contracts_by_id[cid].creditor_id == agent.unique_id and
               agent.model.contracts_by_id[cid].status == ContractStatus.ACTIVE
        ]
        total_agent_principal = sum(c.current_principal for _, c in deposits)

        if total_neighbor_sugar < shortfall or total_agent_principal < shortfall:
            return None

        # --- 2. The "No-Split-First" Greedy Loop ---
        manifest: TransactionManifest = []
        needed_sugar = shortfall
        
        # Sort resources according to heuristics
        deposits.sort(key=lambda item: item[1].current_principal)
        
        while needed_sugar > 1e-6: # Use tolerance for float comparison
            # Find current best resources
            neighbors.sort(key=lambda n: n.sugar, reverse=True)
            
            # Filter out used-up resources
            neighbors = [n for n in neighbors if n.sugar > 1e-6]
            deposits = [(cid, c) for cid, c in deposits if c.current_principal > 1e-6]

            if not neighbors or not deposits:
                break # Ran out of resources

            richest_neighbor = neighbors[0]
            smallest_deposit_id, smallest_deposit = deposits[0]

            # --- 3. The "No-Split" Rule ---
            s_rich = richest_neighbor.sugar
            p_small = smallest_deposit.current_principal
            is_split = False

            if s_rich >= p_small:
                trade_amount = p_small # Use the whole deposit
            else: # s_rich < p_small
                trade_amount = s_rich # Forced to split to get the last sugar
                is_split = True

            # --- 4. Build Manifest Legs for this Trade ---
            sugar_leg = TransferLeg(AssetType.SUGAR, trade_amount, richest_neighbor.unique_id, agent.unique_id)
            deposit_leg = TransferLeg(AssetType.DEMAND_DEPOSIT, trade_amount, agent.unique_id, richest_neighbor.unique_id, asset_id=smallest_deposit_id)
            manifest.extend([sugar_leg, deposit_leg])
            
            # This is a temporary cache used by execute() to know which model function to call.
            # We associate it with the deposit leg's unique tuple representation.
            cls.is_split_trade[(deposit_leg.asset_id, deposit_leg.amount, deposit_leg.dest_agent_id)] = is_split

            # --- 5. Update State for Next Loop Iteration ---
            needed_sugar -= trade_amount
            richest_neighbor.sugar -= trade_amount # Simulate change
            smallest_deposit.current_principal -= trade_amount # Simulate change

        if manifest:
            sugar_generated = shortfall - needed_sugar
            return cls(agent, manifest, sugar_generated)
        
        return None

    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
        """The 'Simulator'. Simply adds the generated sugar to the sim_agent."""
        sim_agent.sugar += self.sugar_to_generate
        return sim_agent.sugar, sim_agent

    def execute(self):
        """The 'Executor'. Reads the manifest and calls the correct model functions."""
        # A bit of a hack to pass the is_split info from the planner to the executor
        is_split_cache = self.__class__.is_split_trade
        
        for leg in self.manifest:
            source_agent = self.agent.model.get_agent_by_id(leg.source_agent_id)
            dest_agent = self.agent.model.get_agent_by_id(leg.dest_agent_id)
            if not source_agent or not dest_agent: continue

            if leg.asset_type == AssetType.SUGAR:
                source_agent.sugar -= leg.amount
                dest_agent.sugar += leg.amount
            
            elif leg.asset_type == AssetType.DEMAND_DEPOSIT:
                key = (leg.asset_id, leg.amount, leg.dest_agent_id)
                is_split = is_split_cache.get(key, False)

                if is_split:
                    original_contract = self.agent.model.contracts_by_id.get(leg.asset_id)
                    if not original_contract: continue
                    remaining_principal = original_contract.current_principal - leg.amount
                    
                    self.agent.model.split_contract(
                        original_contract_id=leg.asset_id,
                        split_definitions=[
                            (remaining_principal, source_agent.unique_id),
                            (leg.amount, dest_agent.unique_id)
                        ]
                    )
                else: # No-split case
                    self.agent.model.transfer_contract_ownership(
                        contract_id=leg.asset_id,
                        new_creditor_id=dest_agent.unique_id
                    )