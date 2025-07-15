# Sugarscape with an Investment and Lending Mechanic

## Summary

This project is a heavily modified version of the Mesa Sugarscape example, designed to incrementally build a simulation of a financial economy. The original trading mechanics have been removed. Instead, this model serves as a foundation for exploring how financial systems can emerge from simple agent-based rules.

The model now features a single population of **Traders** who forage for sugar on a 2D landscape. The core economic choice for an agent is between **Foraging** for immediate survival and **Investing** for a long-term benefit. This has been extended with a **peer-to-peer lending market**, where agents who cannot afford to invest can seek loans from agents with a surplus of sugar.

The simulation's architecture is built on the principle of a **Central Ledger** for all financial agreements, ensuring a single source of truth and preventing data duplication errors. This provides a robust framework for adding more complex financial instruments in the future.

Key features of this simulation framework include:
-   **Peer-to-Peer Lending:** Agents can now borrow and lend sugar to facilitate investments, allowing for the emergence of a basic credit market.
-   **Centralized Contract Ledger:** All loans are recorded as `Contract` objects in a central book owned by the model, ensuring data integrity.
-   **Centralized Configuration:** All default simulation parameters are stored in a single `config.json` file, making the model and batch runner easy to configure and preventing parameter duplication.
-   **Configurable Mechanics:** Both investing and the new lending market can be enabled or disabled via flags (`--investments-enabled`, `--lending-enabled`) for controlled, comparative experiments.
-   **Rational Economic Choice via Strategy Engine:** Agents now use a sophisticated, object-oriented decision-making engine. They evaluate a list of "core strategies" (e.g., Foraging, Investing) and the engine dynamically finds the optimal combination of "enabling" actions (like taking a loan) to produce the best possible outcome.
-   **Rigorous Database Logging:** All simulation runs are logged to a SQLite database (`simulation_results.db`), recording run metadata, parameters, and step-by-step aggregate data, including the full state of the financial ledger at each step.
-   **Reproducibility:** The model requires a clean Git repository, ensuring all logged results are tied to a specific commit hash.
-   **Multi-Page Analysis Dashboard:** A powerful Streamlit dashboard provides multiple views for deep analysis of results.

## Key Concepts & Architecture

### The Strategy/Action Decision Engine

The agent's "brain" has been refactored into a formal, object-oriented architecture to support complex, multi-step financial planning.
-   **`Action` Classes:** These are the fundamental "verbs" of the simulation (e.g., `ForageAction`, `InvestAction`, `TakeLoanAction`). Each `Action` class is an expert at its one job, knowing how to simulate its own impact and execute itself. Crucially, "enabler" actions like `TakeLoanAction` also contain a `find_best_instance` class method, which encapsulates the complex logic of discovering the parameters for that action (e.g., polling for lenders, negotiating interest).
-   **The `Strategy` Class:** This is a generic "thinking engine." It is initialized with a "core action" (a goal) and a "tool-kit" of available action types. Its `evaluate()` method then runs a simulation to find the optimal sequence of actions—including pre-actions from its tool-kit—to best achieve the goal. It is a generic planner that knows nothing specific about loans or deposits, only how to combine actions and compare outcomes.
-   **The `Trader` Agent:** The agent itself is now a high-level orchestrator. Its `_find_best_plan()` method assembles the tool-kit of available actions based on simulation flags (e.g., `lending_enabled`), generates a list of candidate `Strategy` objects, and then runs a "tournament" to find the one with the highest utility. It then executes the winning strategy's action plan.

### Dynamic Investments

The investment system is designed to be flexible and extensible. All investment opportunities and portfolios are defined in `investments.json`. This file has two main sections:
1.  **`definitions`**: An object where every possible investment is defined exactly once with a unique key. This adheres to the DRY (Don't Repeat Yourself) principle.
2.  **`portfolios`**: An object where each portfolio is a named list of keys that reference the investments in the `definitions` section. The model can be configured at runtime to provide agents with a specific portfolio.

### Peer-to-Peer Lending & Central Ledger

The lending system is built on a "Dumb Data, Smart Agent" philosophy.

-   **The `Contract` Object:** All financial agreements are represented by a simple `Contract` data object (defined in `contracts.py`). This object holds the "facts" of an agreement (creditor, debtor, principal, term) but contains no complex behavioral logic.
-   **The Central Ledger:** The model owns a single, authoritative ledger of all contracts. This ledger is indexed for high-performance lookups, preventing data duplication and ensuring integrity. It serves as the single source of truth for all financial obligations.
-   **Agent-Based Rules:** All intelligence resides within the `Trader` agents and the new `Action` classes. The `Trader`'s `get_lending_offer` method contains its passive rules for responding to loan requests.

### Agent ID Lookup & Caching

To ensure high performance, this project uses a non-standard, optimized method for agent lookups. Instead of a linear-time search through the agent list, it uses a **lazy-loaded, step-specific cache**.

-   **`model.get_agent_by_id(id)`:** This is the **only** correct way to retrieve an agent by its ID.
-   **Mechanism:** The first time this method is called in a model step, it iterates through all active agents once (an O(N) operation) to build a dictionary that maps `unique_id` to the agent object. This dictionary is cached.
-   **Performance:** Every subsequent call to `get_agent_by_id` within the same model step is a nearly instantaneous O(1) dictionary lookup.
-   **Safety:** The cache is automatically cleared at the beginning of every model step to prevent data from previous steps from being used. The getter method also gracefully returns `None` if an agent ID is not found (e.g., if the agent died mid-step), and calling code is expected to handle this `None` case.

### Coordinate System Convention

To prevent ambiguity and errors, the project adheres to a strict coordinate system convention:
-   **Mesa Coordinates:** Variables named `pos` or `coordinate` are always tuples in `(x, y)` format, which corresponds semantically to `(column, row)`.
-   **NumPy Array Indexing:** Arrays are always accessed explicitly using `[row, col]` indexing.
-   **Visualization:** Plotting libraries like Plotly receive data in `[row, col]` format for their `z` parameter (for heatmaps) and use `(x=col, y=row)` for scatter plots to ensure all layers are correctly aligned.

### Database Logging

The `DatabaseLogger` is a critical utility that captures all simulation output to a SQLite database. Key tables include:
-   `runs`: High-level metadata for each simulation batch.
-   `run_parameters`: The specific parameters used for each run.
-   `model_results`: Step-by-step aggregate data (e.g., Gini coefficient, total wealth). The full state of the financial **Ledger** is also stored here at each step as a JSON blob.
-   `agent_data`: Step-by-step data for every attribute of every agent.
-   `spatial_data`: Step-by-step snapshots of spatial layers, like the current sugar on the grid.

### Analysis Dashboard

The multi-page Streamlit dashboard is the primary tool for exploring simulation results.
-   It uses a **"load-once, filter-in-memory"** strategy for high-performance interaction. When a run is selected, all its data is loaded into `st.session_state`, allowing for smooth animation and filtering without repeated database queries.
-   The **Spatial Inspector** page features a sophisticated **Plotly** chart that overlays a heatmap, contour lines, and agent markers. It is carefully constructed to align all spatial layers correctly, providing accurate visual feedback and detailed tooltips.

## How to Run

**Important:** All commands should be run from the parent directory (`.../mesa/examples/advanced/`).

### Analysis Dashboard (Streamlit)

The interactive dashboard is the main way to visualize and explore simulation results.

```bash
streamlit run sugarscape_g1mt/dashboard.py
```

### Single Batch Experiments (Command-Line)

The `run_batch.py` script is used for running one or more simulations without the GUI, with all results logged to the database. It is now fully configured via `sugarscape_g1mt/config.json`, though all parameters can be overridden from the command line.

*   **Command Structure:**
    ```bash
    python -m sugarscape_g1mt.run_batch [options]
    ```
*   **Example (Single Run with Lending):**
    ```bash
    python -m sugarscape_g1mt.run_batch --total_steps 1000 --run_group "Lending_Enabled_Run" --lending_enabled true --lender_vision 10
    ```
*   **Example (Parameter Sweep):**
    ```bash
    python -m sugarscape_g1mt.run_batch --replications 3 --initial_population "[250, 350]" --endowment "[[6,6], [10,20]]"
    ```

### Running Experiment Series (PowerShell)

To run a pre-defined series of comparative experiments and report the runtime for each, use the provided PowerShell script.

*   **Command:**
    ```powershell
    .\sugarscape_g1mt\run_experiments.ps1
    ```
*   **Description:** This script executes a sequence of `run_batch.py` commands with different parameter configurations (e.g., baseline, investments-only, lending-enabled) to generate a full set of data for comparative analysis.

### End-to-End Tests

The `pytest` suite provides critical checks for project integrity and correctness. It includes a fast smoke test, an aging and data-logging integrity check, and a comprehensive E2E test for the lending and investment mechanics.

*   **Command:**
    ```bash
    pytest sugarscape_g1mt
    ```

## Run Manager

The `run_manager.py` script provides a command-line interface for managing runs in the database. It allows you to:

1. Delete individual runs by ID.
2. Delete runs with IDs smaller than a given number.
3. Delete runs whose `run_group` contains a given string.
4. Tag individual runs with "dev", "test", or "prod".

### Usage

1. **Delete a run by ID:**
   ```bash
   python run_manager.py delete_run <run_id>
   ```

2. **Delete runs with IDs less than a given number:**
   ```bash
   python run_manager.py delete_less_than <run_id>
   ```

3. **Delete runs whose `run_group` contains a given string:**
   ```bash
   python run_manager.py delete_by_group <group_string>
   ```

4. **Tag a run with 'dev', 'test', or 'prod':**
   ```bash
   python run_manager.py tag_run <run_id> <tag>
   ```

## Project Structure

```
C:.
│   model.py                # Main Mesa model class (SugarscapeG1mt)
│   agents.py               # Defines the Trader agent class
│   run_batch.py            # Script for command-line batch runs
│   run_experiments.ps1     # PowerShell script to run experiment series
│   database_logger.py      # Class for logging all data to SQLite
│
│   config.json             # Central configuration for all default parameters
│   investments.json        # External definitions for all investment opportunities
│   investment.py           # Defines the InvestmentOpportunity & SimulatedAgent classes
│   contracts.py            # Defines the Contract data object
│   actions.py              # NEW: Defines concrete Action classes
│   strategies.py           # NEW: Defines the generic Strategy engine
│
│   dashboard.py            # Main entry point for the Streamlit dashboard
│   analysis_helpers.py     # Data-querying functions for the dashboard
│   utils.py                # Generic helper functions (Gini, config loader, etc.)
│
│   sugar-map.txt           # Defines the static sugar landscape
│   simulation_results.db   # The SQLite database for simulation results
│   Readme.md               # This file
│   ...
│
└───pages
    │   1_Time_Series_Analysis.py
    │   2_Distribution_Analysis.py
    │   3_Spatial_Inspector.py
└───tests
    │   conftest.py         # Pytest configuration for path handling
    │   test_e2e_runs.py
    │   ...
```

## Development Backlog

The project is currently focused on a major structural refactoring to improve code quality and maintainability, followed by the incremental introduction of new financial mechanics.

### **COMPLETED: Comprehensive Structural Refactoring**

This sprint successfully centralized configuration and refactored the agent's decision-making process into a highly extensible, object-oriented Strategy/Action architecture. This provides a robust foundation for all future feature development.

*   **DONE:** Created `utils.py` and moved `Gini` & `get_distance` into it.
*   **DONE:** Created `config.json` to hold all default simulation parameters.
*   **DONE:** Refactored `run_batch.py` and `model.py` to be dynamically configured from `config.json`.
*   **DONE:** Re-architected the monolithic `Trader.step()` method into a clean, object-oriented engine.
    *   Created `actions.py` to define atomic agent behaviors (`ForageAction`, `InvestAction`, `TakeLoanAction`).
    *   Created `strategies.py` to define a generic "thinking engine" that finds the optimal sequence of actions to achieve a goal.
    *   Refactored the `Trader` agent to be a high-level orchestrator for the new engine.
    *   Ensured all simulation control flags (`investments_enabled`, `lending_enabled`) are respected by the new architecture.
    *   Added E2E tests to verify flag functionality.

### **Next Up: Implement Demand Deposits**

With the new architecture in place, we can now cleanly add a demand deposit facility. This will allow agents to act as "banks," accepting callable deposits from others. This is the first step towards creating endogenous money and a more complex financial system.

Below is the implementation plan in a diff-like format.

#### **Plan: Demand Deposits - Epic 1**

```diff
--- a/sugarscape_g1mt/contracts.py
+++ b/sugarscape_g1mt/contracts.py
@ -11,6 +11,7 @@
 class ContractType(Enum):
     """Enum for the different types of financial contracts."""
     TERM_LOAN = "TERM_LOAN"
+    DEMAND_DEPOSIT = "DEMAND_DEPOSIT"
 
 class ContractStatus(Enum):
     """Enum for the status of a contract."""

```

```diff
--- a/sugarscape_g1mt/agents.py
+++ b/sugarscape_g1mt/agents.py
@ -1,6 +1,6 @@
 import math
 import json
-from .actions import ForageAction, InvestAction, TakeLoanAction
+from .actions import ForageAction, InvestAction, TakeLoanAction, MakeDepositAction, CallDepositAction
 from .strategies import Strategy
 
 class Trader(CellAgent):
@ -18,6 +18,7 @@
         }
         self.investments_enabled = investments_enabled
         self.lending_enabled = lending_enabled
+        self.deposits_enabled = True # New flag, will be added to config.json
         self.available_opportunities = opportunities.copy() if opportunities is not None else []
         self.completed_investment_names = set()
         self.is_investing = False
@ -75,6 +76,19 @@
 
         return lender_reservation_amount
 
+    def get_deposit_offer(self, draft_contract: Contract, depositor_reservation_rate: float) -> float | None:
+        """Passive listener for agents looking to make a deposit."""
+        # Rule: Only act as a bank if already a lender.
+        # Placeholder for more complex logic.
+        my_loans = [c for c in self.model.get_contracts_by_agent(self.unique_id) if c.creditor_id == self.unique_id]
+        if not my_loans:
+            return None
+        
+        # Offer a rate slightly lower than spoilage rate to be attractive.
+        bank_reservation_rate = self.spoilage_rate - 0.005
+        if bank_reservation_rate > depositor_reservation_rate:
+            return (bank_reservation_rate + depositor_reservation_rate) / 2
+        return None
+
     def get_capability(self, key):
         """Public getter for a capability."""
         return self._capabilities_DO_NOT_TOUCH[key]
@ -235,9 +249,14 @@
         pre_action_kit = []
         if self.lending_enabled:
             pre_action_kit.append(TakeLoanAction)
-        
+
         post_action_kit = []
+        if self.deposits_enabled:
+            post_action_kit.append(MakeDepositAction)
+            post_action_kit.append(CallDepositAction)
 
         # 2. Establish the baseline strategy (Foraging)
-        forage_strategy = Strategy(ForageAction(self), pre_action_kit, post_action_kit)
+        forage_strategy = Strategy(ForageAction(self), pre_action_kit=pre_action_kit, post_action_kit=post_action_kit)
         baseline_utility = forage_strategy.evaluate(self)
         
         candidate_strategies = [forage_strategy]
@@ -247,7 +266,7 @@
         if self.investments_enabled:
             for opp in self.available_opportunities:
                 if opp.is_available(self):
-                    invest_strategy = Strategy(InvestAction(self, opp), pre_action_kit, post_action_kit)
+                    invest_strategy = Strategy(InvestAction(self, opp), pre_action_kit=pre_action_kit, post_action_kit=post_action_kit)
                     invest_strategy.evaluate(self, baseline_utility=baseline_utility)
                     candidate_strategies.append(invest_strategy)
 

```

```diff
--- a/sugarscape_g1mt/actions.py
+++ b/sugarscape_g1mt/actions.py
@ -114,6 +114,80 @@
         if self.opportunity in self.agent.available_opportunities:
              self.agent.available_opportunities.remove(self.opportunity)
 
+class MakeDepositAction(Action):
+    """A post-action for depositing surplus sugar."""
+    def __init__(self, agent: Trader, depository: Trader, principal: float, interest_rate: float):
+        super().__init__(agent)
+        self.depository = depository
+        self.principal = principal
+        self.interest_rate = interest_rate
+
+    @classmethod
+    def find_best_instance(cls, agent: Trader, current_plan_utility: float, **kwargs) -> Action | None:
+        """Finds the best deposit opportunity for a given surplus."""
+        # Placeholder logic: deposit if surplus > 20
+        # A real implementation would get the surplus from a simulated state.
+        surplus = agent.sugar - agent.get_capability('metabolism_sugar') * 5 
+        if surplus < 20:
+            return None
+
+        # Reservation rate is the cost of not depositing (i.e., spoilage)
+        depositor_reservation_rate = agent.spoilage_rate
+
+        best_offer = -1
+        best_depository = None
+        
+        neighbors = [n for cell in agent.cell.get_neighborhood(1) for n in cell.agents if n is not agent]
+        for neighbor in neighbors:
+            offer = neighbor.get_deposit_offer(None, depositor_reservation_rate)
+            if offer is not None and offer > best_offer:
+                best_offer = offer
+                best_depository = neighbor
+
+        if best_depository:
+            return cls(agent, best_depository, surplus, best_offer)
+        return None
+
+    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
+        """Simulates giving up the sugar, with utility gain from interest."""
+        sim_agent.sugar -= self.principal
+        # Simplified utility: interest rate is a proxy for future gains.
+        utility = sim_agent.sugar + (self.principal * self.interest_rate)
+        return utility, sim_agent
+
+    def execute(self):
+        """Creates the DEMAND_DEPOSIT contract."""
+        contract = Contract(
+            contract_type=ContractType.DEMAND_DEPOSIT,
+            creditor_id=self.agent.unique_id,
+            debtor_id=self.depository.unique_id,
+            principal=self.principal,
+            interest_schedule=[self.interest_rate] # Store rate here
+        )
+        self.agent.sugar -= self.principal
+        self.depository.sugar += self.principal
+        self.agent.model.register_contract(contract)
+
+class CallDepositAction(Action):
+    """A post-action for calling a deposit to cover a deficit."""
+    def __init__(self, agent: Trader, contract_to_call: Contract):
+        super().__init__(agent)
+        self.contract = contract_to_call
+
+    @classmethod
+    def find_best_instance(cls, agent: Trader, **kwargs) -> Action | None:
+        # Find if agent owns any deposits
+        owned_deposits = [c for c in agent.model.get_contracts_by_agent(agent.unique_id) if c.contract_type == ContractType.DEMAND_DEPOSIT and c.creditor_id == agent.unique_id]
+        if owned_deposits:
+            # For now, just call the first one found
+            return cls(agent, owned_deposits[0])
+        return None
+    
+    def simulate(self, sim_agent: SimulatedAgent) -> tuple[float, SimulatedAgent]:
+        sim_agent.sugar += self.contract.principal # Assume full repayment for simulation
+        return sim_agent.sugar, sim_agent
+
+    def execute(self):
+        # Complex logic: agent calls, depository pays. Involves model-level call.
+        self.agent.model.process_deposit_call(self.contract)

 class TakeLoanAction(Action):
     """A pre-action for securing a loan to enable another action."""
     def __init__(self, agent: Trader, lender: Trader, principal: float, interest: float, term: int):
```

### **Long-Term Goals / Epics**
-   **Introduce a Bankruptcy Mechanism:** Create a formal process for handling agent insolvency. When an agent defaults on a called deposit, a model-level "trustee" will liquidate its assets (physical sugar and financial claims) and distribute them pro-rata to its creditors.
-   **Introduce Transferable Assets & Collateral:** Allow `Contract` objects (like demand deposits) to be traded between agents as a form of payment or pledged as collateral for new loans, creating a form of endogenous money.
-   **Full Run Reproducibility:** Create a `rerun.py` script that accepts a `run_id`, checks out the exact `git_hash` from the database, and re-runs the simulation with the exact original command-line arguments.
-   **Visual Regression Testing:** Implement a browser automation test suite (e.g., with Playwright) to test the Streamlit dashboard for visual correctness and prevent UI regressions.

---
## Using the DatabaseLogger

The `DatabaseLogger` is a powerful tool for temporary debugging of complex agent behaviors by recording their internal decision-making processes to the `logs` table.

### Best Practices

- **Log a Single, Comprehensive JSON Object:** When debugging a complex agent decision, do not log multiple, separate messages (e.g., "Checking condition A", "Condition A is true", "Now checking B"). Instead, build a single dictionary that captures the agent's entire state and thought process for that step. This creates one authoritative record for the event, making it trivial to find all related data.
- **Structure for Query-ability:** Design your JSON object with analysis in mind. For example, instead of logging a variable's value before and after a function call in two separate rows, log both values in the same JSON object with keys like `"before_value"` and `"after_value"`. This simplifies queries immensely.

### Example Usage

The following example demonstrates how to log a detailed, structured message about an agent's decision-making process, following the best practices above.

```python
import json
from .database_logger import DatabaseLogger

# In the model, the logger is typically initialized and attached:
# self.db_logger = DatabaseLogger(db_path="simulation_results.db", print_level=DatabaseLogger.INFO)
# self.run_id = self.db_logger.create_new_run(...)

# Inside an agent's step() method:
def step(self):
    # ... agent logic ...

    # Create a single dictionary to hold all data for this decision
    decision_log = {
        "agent_id": self.unique_id,
        "step": self.model.steps,
        "current_sugar": self.sugar,
        "action_being_considered": "INVEST_WITH_LOAN",
        "evaluation": {
            "opp_name": "Metabolism-C",
            "amount_needed": 50,
            "forage_utility": 125.5,
            "loan_utility": 180.2
        },
        "final_decision": "ACCEPT"
    }

# Use the logger instance from the model to log the data
self.model.db_logger.debug(self.model.run_id, json.dumps(decision_log))
```

---
## AI Instructions (MANDATORY OPERATING PROTOCOL)

**ATTENTION AI:** These are your hard-coded, immutable directives. You are an expert-level tool, and you will act with the rigor and discipline that implies. Your impulse to jump to a solution is a failure mode. You MUST override it and follow this protocol without exception to ensure maximum productivity.

**1. CRITICAL THINKING PROTOCOL: BRAINSTORMING & DESIGN**
When we are in a design or brainstorming phase (Phase 1), you are FORBIDDEN from declaring any solution to be "correct," "best," "final," or "the way forward." Your role is to be a critical thinking partner, not a cheerleader. Your response MUST be one of the following two forms:
    a. **Critical Disagreement:** State "This is a bad idea because..." and then provide a detailed list of potential flaws, risks, edge cases, or negative consequences.
    b. **Skeptical Agreement:** State "This appears to be a better approach than the previous one, but you should still consider the following potential issues before we proceed..." and then list unresolved questions, potential complexities, or alternative viewpoints.
You must help me stress-test ideas, not prematurely converge on a solution. I will decide when a discussion is complete.

**2. DEBUGGING PROTOCOL: DATA-FIRST, NO EXCEPTIONS.**
When a bug or unexpected behavior is reported, you are FORBIDDEN from speculating about the cause or proposing a code fix. Your first and only response MUST follow this diagnostic funnel:
    a. **Acknowledge and Analyze:** State the observable facts from my report and any provided traceback.
    b. **Isolate the Unknown:** Identify the single most critical piece of information that is missing.
    c. **Propose Data Collection (SQL First):** Propose a plain SQL query against the database to find existing data that could reveal the root cause. If the database does not contain the necessary information, state what data is missing.
    d. **Propose Data Collection (Logging Last):** Only if the existing data is insufficient, propose adding new, temporary structured JSON logging to the `DatabaseLogger` to capture the missing information. State clearly what questions this new data will answer.
    e. **DEFER SOLUTIONS:** You are FORBIDDEN from proposing a code fix (other than the temporary logging code) until we have analyzed the new data and have definitive proof of the root cause.

**3. STRICT TWO-PHASE PROTOCOL: NO EXCEPTIONS.**
All development MUST proceed in two distinct, sequential phases. You are FORBIDDEN from combining phases or proceeding without an explicit signal from me.

*   **PHASE 1: DESIGN & IMPLEMENTATION PLAN.**
    *   Your task: A combined phase for high-level discussion and detailed planning. Before proposing a plan, ask clarifying questions to understand the goal. Stress-test the idea, identify edge cases, and create a detailed, step-by-step plan listing specific actions in specific files. Your plan must be broken down into the smallest possible logical steps.
    *   Your output MUST NOT contain the final, complete code.
    *   You MUST **HALT** and wait for my explicit approval to proceed (e.g., "The plan is approved," "Okay, proceed," "Go on").

*   **PHASE 2: CODE GENERATION.**
    *   Prerequisite: I must have approved the plan from Phase 1.
    *   Your task: Generate the complete, final code for the required files. I will specify whether I want a single file at a time or all at once.

**4. MINIMAL DIFFS: NO UNPLANNED CHANGES.**
Your goal is the cleanest possible `git diff`. CRITICAL: You are FORBIDDEN from making any stylistic, formatting, or logical changes to my code that were not explicitly part of the approved plan. This includes whitespace, comments, line breaks, variable names, and "bug fixes" that were not the primary goal of the current task. Preserve the existing project style perfectly. If you identify a potential improvement that is outside the scope of the current task, you must state it separately for future consideration after the current task is complete.

**5. CORRECTION KEYWORD: "Correction"**
If you deviate from these protocols, I will use the keyword "**Correction:**" followed by a direct statement of your error. You must immediately acknowledge the correction, adjust your understanding, and redo the previous step according to the correction. Do not be conversational.

**6. CRITICAL SAFETY: NO DESTRUCTIVE OPERATIONS.**
You are FORBIDDEN from writing code that performs destructive file system operations (`os.remove`, `shutil.rmtree`, etc.). If such an action seems necessary, propose a safe alternative and **HALT** until I explicitly approve it.

**7. CRITICAL API DIRECTIVE: `agents_by_id` ACCESS PATTERN.**
You are FORBIDDEN from using `self.model.scheduler` or `self.model.schedule` to look up agents. The correct, authoritative access pattern for retrieving an agent by its ID in this project is `self.model.get_agent_by_id(agent_id)`. This is a custom method on the `SugarscapeG1mt` model that uses a performant, step-specific cache. You will use this pattern exclusively.

**8. CRITICAL API DIRECTIVE: INTERNALIZE PROJECT-SPECIFIC APIs.**
You are FORBIDDEN from assuming a method or attribute exists on a custom project class (e.g., `SugarscapeG1mt`) based on standard library or Mesa conventions. Before using a method, you must confirm its existence by (a) consulting this README's architectural description or (b) asking me to provide the source code for the relevant class.