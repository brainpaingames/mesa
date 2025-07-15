# sugarscape_g1mt/strategies.py

from __future__ import annotations
import math
import json
from typing import TYPE_CHECKING, List, Type

from .actions import Action, InvestAction, TakeLoanAction
from .investment import SimulatedAgent
from .contracts import Contract, ContractType

if TYPE_CHECKING:
    from .agents import Trader
    from .investment import InvestmentOpportunity

class Strategy:
    """
    Represents a complete, potential plan for an agent's turn.
    A Strategy is initialized with a "core" action and a "tool-kit" of
    available action types. It is responsible for evaluating the utility
    of the core action, including finding and adding any necessary "pre-actions"
    (like taking a loan) or "post-actions" to optimize its outcome.
    """
    def __init__(self, core_action: Action, pre_action_kit: List[Type[Action]] = None, post_action_kit: List[Type[Action]] = None):
        self.core_action = core_action
        
        self.pre_action_kit = pre_action_kit or []
        self.post_action_kit = post_action_kit or []
        
        self.final_plan: list[Action] = []
        self.utility: float = -math.inf
        self.is_evaluated: bool = False

    def get_action_plan(self) -> list[Action]:
        """Returns the final, ordered list of actions for execution."""
        return self.final_plan

    def evaluate(self, agent: Trader, baseline_utility: float = 0) -> float:
        """
        The main "thinking engine". It evaluates all valid combinations of pre-
        and post-actions around the core action and selects the best one.

        Args:
            agent: The agent making the decision.
            baseline_utility: The utility of the default action (e.g., foraging),
                              used for context in negotiations.

        Returns:
            The final utility score for the best version of the plan.
        """
        if self.is_evaluated:
            return self.utility

        candidate_plans = []

        # --- Plan A: The "Naked" Core Action ---
        naked_plan = [self.core_action]
        naked_utility, _ = self._simulate_plan(agent, naked_plan)
        candidate_plans.append((naked_utility, naked_plan))
        
        # --- Pre-Action Analysis (The "Enablers") ---
        potential_enablers = self.core_action.get_enabler_action_types()
        available_enablers = [ptype for ptype in potential_enablers if ptype in self.pre_action_kit]

        for enabler_type in available_enablers:
            # Ask the Action class to find the best instance of itself
            enabler_action = enabler_type.find_best_instance(
                agent=agent,
                core_action_to_enable=self.core_action,
                baseline_utility=baseline_utility
            )

            if enabler_action:
                # If an enabler was found, create and evaluate a new plan
                new_plan = [enabler_action, self.core_action]
                new_utility, _ = self._simulate_plan(agent, new_plan)
                candidate_plans.append((new_utility, new_plan))
        
        # --- Find the best core plan (with or without pre-actions) ---
        best_core_utility, best_core_plan = max(candidate_plans, key=lambda item: item[0])
        
        # --- Post-Action Analysis (The "Optimizers" and "Rebalancers") ---
        current_best_plan = best_core_plan
        current_best_utility = best_core_utility
        
        if self.post_action_kit and current_best_utility > -math.inf:
            # First, get the simulated state *after* the best core plan has run
            _, final_sim_agent_state = self._simulate_plan(agent, current_best_plan)

            for post_action_type in self.post_action_kit:
                # Ask the PostAction class to find an instance of itself based on the final state
                post_action = post_action_type.find_best_instance(
                    agent=agent, 
                    sim_agent_state=final_sim_agent_state, 
                    core_action_utility=current_best_utility
                )

                if post_action:
                    # If a beneficial post-action is found, simulate it and update the plan
                    # Note: We are currently only evaluating ONE post-action, not chains.
                    # The simulation is based on the state *before* this post-action.
                    new_plan_with_post_action = current_best_plan + [post_action]
                    new_utility, _ = self._simulate_plan(agent, new_plan_with_post_action)
                    
                    if new_utility > current_best_utility:
                        # This logic is intentionally simple for now: if a post-action
                        # improves things, we adopt it. It doesn't re-evaluate other post-actions.
                        current_best_utility = new_utility
                        current_best_plan = new_plan_with_post_action
                        # We also need to update the sim_agent_state for the next iteration
                        _, final_sim_agent_state = self._simulate_plan(agent, current_best_plan)


        # --- Finalize the strategy's outcome ---
        self.utility = current_best_utility
        self.final_plan = current_best_plan
        self.is_evaluated = True
        
        return self.utility

    def _simulate_plan(self, agent: Trader, plan: List[Action]) -> tuple[float, SimulatedAgent]:
        """Helper to simulate a complete sequence of actions."""
        sim_agent = SimulatedAgent(agent)
        final_utility = -math.inf

        for action in plan:
            final_utility, sim_agent = action.simulate(sim_agent)
            if final_utility == -math.inf:
                # If any step in the plan fails, the whole plan fails.
                return -math.inf, sim_agent
        
        return final_utility, sim_agent