# sugarscape_g1mt/strategies.py
from __future__ import annotations
import math
import json
from typing import TYPE_CHECKING

from .actions import Action, InvestAction, TakeLoanAction
from .investment import SimulatedAgent
from .contracts import Contract, ContractType

if TYPE_CHECKING:
    from .agents import Trader
    from .investment import InvestmentOpportunity

class Strategy:
    """
    Represents a complete, potential plan for an agent's turn.
    A Strategy is initialized with a "core" action and is responsible for
    evaluating the utility of that action, including finding and adding any
    necessary "pre-actions" (like taking a loan) to make it possible, or
    "post-actions" (like making a deposit) to optimize its outcome.
    """
    def __init__(self, core_action: Action):
        self.core_action = core_action
        
        # These will be populated during the evaluation phase
        self.pre_actions: list[Action] = []
        self.post_actions: list[Action] = []
        
        self.utility: float = -math.inf
        self.is_evaluated: bool = False

    def get_action_plan(self) -> list[Action]:
        """Returns the final, ordered list of actions for execution."""
        return self.pre_actions + [self.core_action] + self.post_actions

    def evaluate(self, agent: Trader, baseline_utility: float = 0) -> float:
        """
        The main "thinking engine". It evaluates the utility of a complete plan
        built around the core action. This is where the "pre- and post-bundle"
        logic lives.

        Args:
            agent: The agent making the decision.
            baseline_utility: The utility of the default action (e.g., foraging),
                              used for context in negotiations.

        Returns:
            The final utility score for the best version of the plan.
        """
        if self.is_evaluated:
            return self.utility

        # --- Phase 1: Simulate the "naked" core action ---
        initial_sim_agent = SimulatedAgent(agent)
        final_utility, state_after_core = self.core_action.simulate(initial_sim_agent)

        # --- Phase 2: Pre-Action Analysis (The "Enablers") ---
        # If the core action failed, can we enable it with a pre-action?
        if final_utility == -math.inf:
            if isinstance(self.core_action, InvestAction):
                # Try to find a loan to enable this failed investment
                loan_action = self._find_best_loan_for_investment(agent, self.core_action, baseline_utility)
                if loan_action:
                    self.pre_actions.append(loan_action)
                    
                    # Re-simulate with the full sequence
                    sim_state = SimulatedAgent(agent)
                    # Simulate pre-action
                    _, sim_state = loan_action.simulate(sim_state)
                    # Simulate core action with the new state
                    final_utility, state_after_core = self.core_action.simulate(sim_state)

        # If the plan is still not viable, its utility is infinitely bad.
        if final_utility == -math.inf:
            self.utility = -math.inf
            self.is_evaluated = True
            return self.utility

        # --- Phase 3: Post-Action Analysis (The "Optimizers") ---
        # (This phase is currently a placeholder, ready for deposit logic)
        final_sim_state = state_after_core
        # The final utility is already calculated by the chained simulation.
        # We might add post-action utility here in the future.
        
        # --- Phase 4: Final Utility Calculation ---
        self.utility = final_utility
        self.is_evaluated = True
        return self.utility

    def _find_best_loan_for_investment(self, agent: Trader, invest_action: InvestAction, baseline_utility: float) -> TakeLoanAction | None:
        """
        Finds the best available loan from neighbors to fund a specific investment.
        This logic is ported directly from the old agents.py and removes all placeholders.
        """
        opportunity = invest_action.opportunity
        
        # Calculate how much sugar is needed
        survival_cost = opportunity.cost["metabolism_during_investment"] * (opportunity.cost["duration"] + 1)
        shortfall = max(0, survival_cost - agent.sugar)
        amount_needed = shortfall
        if amount_needed <= 0:
            return None
        
        term = opportunity.cost["duration"] + 10
        
        # 1. Simulate a zero-interest loan to find the best-case utility
        draft_contract = Contract(ContractType.TERM_LOAN, -1, agent.unique_id, amount_needed, term, agent.model.steps, [0])
        utility_zero_interest, death_zero_interest = invest_action.calculate_utility_with_loan(agent, draft_contract)
        
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
            # Reusing the existing passive listener on the lender agent
            lender_offer = lender.get_lending_offer(draft_contract, reservation_amount)
            if lender_offer is not None:
                # 4. If offer is good, finalize the deal
                final_interest = (reservation_amount + lender_offer) / 2
                return TakeLoanAction(agent, lender, amount_needed, final_interest, term)
        
        return None