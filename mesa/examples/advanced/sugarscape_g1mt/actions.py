# sugarscape_g1mt/actions.py
from __future__ import annotations
import math
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .contracts import Contract, ContractType
from .investment import SimulatedAgent

if TYPE_CHECKING:
    from .agents import Trader
    from .investment import InvestmentOpportunity
    from .strategies import Strategy

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


class TakeLoanAction(Action):
    """A pre-action for securing a loan to enable another action."""
    def __init__(self, agent: Trader, lender: Trader, principal: float, interest: float, term: int):
        super().__init__(agent)
        self.lender = lender
        self.principal = principal
        self.interest = interest
        self.term = term

    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
        """Simulates receiving the loan principal."""
        sim_agent.sugar += self.principal
        # Taking a loan does not change the total utility of the state itself,
        # it just enables other actions. The utility is reflected in the final sugar.
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