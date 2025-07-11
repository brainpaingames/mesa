import math
import copy
from .contracts import ContractType, ContractStatus

class InvestmentOpportunity:
    """
    Represents a single investment an agent can make.
    """
    def __init__(self, config_data, model_context=None):
        self.name = config_data.get("name")
        self.requirements = config_data.get("requirements", {})
        self.cost = config_data.get("cost", {})
        self.reward = config_data.get("reward", {})
        
        # This allows rewards to reference model-level parameters, like look-ahead horizon
        if model_context and "agent_look_ahead_horizon" in self.reward:
            self.reward["agent_look_ahead_horizon"] = model_context.agent_look_ahead_horizon

    def is_available(self, agent):
        """Checks if the agent meets the prerequisites for this investment."""
        required_prerequisites = set(self.requirements.get("prerequisites", []))
        return required_prerequisites.issubset(agent.completed_investment_names)

    def calculate_utility(self, agent, horizon, hypothetical_loan=None):
        """
        Calculates the forecasted utility (final sugar) of undertaking this investment.
        Returns a tuple of (utility, is_death).
        """
        if isinstance(agent, SimulatedAgent):
            sim_agent = agent
        else:
            sim_agent = SimulatedAgent(agent)
        
        # Get the agent's current contracts for the simulation
        agent_contract_ids = sim_agent.real_agent.model.contracts_by_agent.get(sim_agent.real_agent.unique_id, set())
        agent_contracts = [sim_agent.real_agent.model.contracts_by_id[cid] for cid in agent_contract_ids if sim_agent.real_agent.model.contracts_by_id[cid].status == ContractStatus.ACTIVE]

        if hypothetical_loan:
            agent_contracts.append(hypothetical_loan)

        # 1. Simulate survival during the investment period
        cost_duration = self.cost["duration"]
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

            sim_agent.sugar -= self.cost["metabolism_during_investment"]
            if sim_agent.sugar <= 0:
                return -1, True # Agent dies during investment
        
        # 2. Apply the reward and forecast the rest of the horizon
        self.apply_reward_to(sim_agent)
        
        remaining_horizon = horizon - metabolism_cost_steps
        if remaining_horizon > 0:
            expected_harvest = sim_agent.get_max_potential_harvest()
            metabolism = sim_agent.get_capability("metabolism_sugar")
            
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
                sim_agent.sugar -= metabolism
                if sim_agent.sugar <= 0:
                    return -1, True # Dies after investing, but before horizon ends
        
        return sim_agent.sugar, False

    def apply_reward_to(self, agent):
        """Applies the investment's rewards to the given agent."""
        for key, value in self.reward.items():
            agent.set_capability(key, value)


class SimulatedAgent:
    """
    A lightweight, temporary agent for 'what-if' scenarios in utility calculations.
    It mimics a real agent's state and capabilities but avoids deep object copies.
    """
    def __init__(self, real_agent):
        self.real_agent = real_agent
        self.sugar = real_agent.sugar
        # Must be a deep copy so changes don't affect the real agent's dictionary
        self._capabilities = copy.deepcopy(real_agent._capabilities_DO_NOT_TOUCH)

    def get_capability(self, key):
        return self._capabilities.get(key)
    
    def set_capability(self, key, value):
        self._capabilities[key] = value

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
        multipliers = self.get_capability("harvest_multipliers")
        # Accesses the real model's static sugar distribution map
        capacity = int(self.real_agent.model.sugar_distribution[cell.coordinate[1], cell.coordinate[0]])
        return cell.sugar * multipliers[capacity]