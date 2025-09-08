Of course. I have made the following edits to the README file:
1.  **Removed Obsolete Sections:** I have completely removed the old `### Dynamic Investments` section, as it described the now-deleted `investments.json` system.
2.  **Updated Project Structure:** I have removed `investments.json` and `investment.py` from the file tree diagram.
3.  **Added New Section:** I have added a new `### Dynamic, Level-Based Investments` section to accurately describe the new "Constant Payback" model.
4.  **Updated Development Backlog:** I have created a new `IN PROGRESS` section detailing the entire diagnostic and design journey we just completed for the new investment model. It serves as a record of the work and clearly states the immediate next steps.

Here is the complete, updated `Readme.md` file.

---

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

### Dynamic, Level-Based Investments

The investment system has been refactored away from a static list of choices to a single, dynamic, and infinitely progressing "Harvesting Technology" track.
-   **Agent State:** Each agent tracks its progress via a `harvest_investment_level` attribute.
-   **Dynamic Calculation:** The costs and benefits of investing to the *next* level are not stored in a file but are calculated on-the-fly by a set of core economic functions designed to create a stable, long-term growth trajectory.
-   **Capital Requirement Model:** The "cost" of an investment is not an upfront payment, but a **capital requirement** an agent must possess to begin investing. This requirement is the total metabolic drain during the fixed-duration investment period. The `metabolism_during_investment` for each level is dynamically derived from the benefit function to ensure the core economic model remains stable and profitable at all levels.

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

### **COMPLETED: Design & Implement Asset Liquidation (Endogenous Money V1)**

This sprint successfully designed the foundational architecture for transferable assets and endogenous money. The core achievement is a new, self-contained agent capability, `ConvertDepositToSugarAction`, which allows an agent to liquidate its `DEMAND_DEPOSIT` contracts to raise physical sugar for other economic activities, such as funding an investment.

This was a major architectural step, establishing the patterns for all future asset transfers.

*   **DONE:** Designed a generic, extensible **Transaction Manifest** architecture (`transactions.py`) composed of `TransferLeg`s. This separates the *description* of a trade from its *execution* and is capable of handling any future asset type.
*   **DONE:** Upgraded the **Central Ledger** with two distinct, authoritative bookkeeping methods on the `model`:
    *   `split_contract`: For when a trade requires splitting a contract into multiple smaller ones (the "Retire and Create" pattern).
    *   `transfer_contract_ownership`: A simpler method for when an entire contract is transferred whole, which updates the `creditor_id` and all necessary ledger indexes.
*   **DONE:** Enhanced the `Contract` object to support **lineage tracking** (`parent_contract_id`, `child_contract_ids`), creating a full audit trail for all split and transfer operations.
*   **DONE:** Implemented the full logic for the `ConvertDepositToSugarAction`, a new "enabler" action that fits perfectly into the existing `Strategy` engine.
*   **DONE:** The action's "brain" (`find_best_instance` method) uses a sophisticated but simple **"No-Split-First" greedy heuristic**. The agent iteratively finds the best possible trade it can make with its neighbors, prioritizing using up small, whole deposits over being forced to split larger ones.

### **COMPLETED: Implement Demand Deposits**

This sprint successfully introduced a demand deposit facility, allowing agents to place surplus sugar with other agents acting as "banks." This was a major step towards creating a more complex financial system.

*   **DONE:** Added `DEMAND_DEPOSIT` contract type and enhanced the `Contract` object to support fractional balances (`current_principal`).
*   **DONE:** Upgraded the `Strategy` engine to evaluate and append "post-actions," enabling agents to make rebalancing decisions (like depositing a surplus) after their primary action.
*   **DONE:** Implemented `MakeDepositAction` and `CallDepositAction` to encapsulate the logic for making and withdrawing deposits.
*   **DONE:** Corrected the `MakeDepositAction.simulate` utility calculation to use a one-step lookahead heuristic, allowing the `Strategy` engine to correctly value the long-term benefit of avoiding spoilage.
*   **DONE:** Implemented `get_deposit_offer` on the `Trader` agent, creating an emergent market for deposit interest rates based on the bank's lending activity.
*   **DONE:** Added an end-to-end test to verify that deposit contracts are created under the right economic conditions.

### **Next Up: Introduce Equity & Bankruptcy**

Now that assets can be liquidated and their ownership transferred, we can introduce equity as a new type of financial asset. This will allow for more sophisticated capital structures and enable the implementation of regulatory constraints like capital adequacy ratios. This epic will also require creating a formal bankruptcy process.

#### **Brainstorming: The "Book Value Equity" Model**

To focus on regulatory aspects first, we can bootstrap the equity market with a simplified, non-negotiable pricing model.
*   **Balance Sheet:** Each agent will have an implicit balance sheet (`Assets = Liabilities + Equity`). Assets include sugar and financial claims; liabilities include loans and deposits taken. `Equity` is the agent's net worth.
*   **Fixed Price:** The price of a "share" of an agent's equity will be fixed based on its current book value (e.g., `Price = 0.01 * Agent.Equity`). This avoids complex valuation AI for now.
*   **Regulatory Push (Forced Issuance):** A new rule will force agents acting as banks to issue and offer equity for sale if their capital ratio (`Equity / Assets`) falls below a global minimum.
*   **Regulatory Pull (Forced Purchase):** A new rule will compel agents making deposits to use a portion of their deposit to first buy equity in the bank, creating a guaranteed market and aligning interests.
*   **Dividends as "Foraging Tax":** To give equity value, shareholders will receive dividends. A simple, robust mechanism is to treat dividends as a "tax" on an agent's gross foraging income, paid out pro-rata to shareholders.

#### **Brainstorming: Bankruptcy & Default Dynamics**

When an agent fails, a formal bankruptcy proceeding must occur to handle its outstanding financial claims.
*   **Trigger:** Agent is removed from the simulation (starvation or old age).
*   **Liquidation:** The model will liquidate the agent's financial assets (e.g., call all its deposits from other banks).
*   **The Waterfall:** The agent's remaining sugar is paid out to its creditors in a strict order of priority:
    1.  **Depositors** are paid first.
    2.  **Lenders (debt holders)** are paid next, if any sugar remains.
    3.  **Equity Holders** are paid last.
*   **The Equity Wipeout:** In almost all cases, the shareholders get nothing. Their `EQUITY_SHARE` contracts are deleted, and they realize a total loss on their investment. This makes equity the riskiest asset class, as it should be.


*   **DONE:** Added `DEMAND_DEPOSIT` contract type.
*   **DONE:** Upgraded the `Strategy` engine to evaluate and append "post-actions."
*   **DONE:** Implemented `MakeDepositAction` and `CallDepositAction`.
*   **DONE:** Implemented `get_deposit_offer` on the `Trader` agent.

### **IN PROGRESS: Major Refactor of Investment Economics**
This work addresses a fundamental flaw discovered in the previous investment model, which led to an economic "bust" where all investment activity ceased in the late game.

*   **Problem Diagnosis:** Through detailed logging and analysis, we discovered that previous investment models were fundamentally unstable. Models with an **unbounded time cost** created a "Shrinking Horizon Problem," making high-level investments appear irrational. Models with simple exponential cost and linear benefit were also proven to be unprofitable within the agent's limited forecast window.

*   **New Design Requirements:** To solve this, we established a new, rigorous set of requirements for the economic "physics":
    1.  **Constant Time Cost:** The `duration` of all investments is a single, fixed parameter.
    2.  **Constant "Time to Save":** The time an agent must save to afford the next investment (if on optimal land) must be a constant `K` at all levels.
    3.  **Constant Relative Return:** The percentage return on investment, as calculated within the agent's forecast, must be constant at all levels.
    4.  **Profitability Constraint:** All economic parameters must be chosen to satisfy a core constraint to ensure investment is always a rational choice.

*   **The "Constant Payback" Model:** We designed a new economic model to meet these requirements:
    1.  **Benefit (Harvest Multiplier):** The agent's productivity grows exponentially with its investment level: `Multiplier(L) = base * (growth_factor ^ L)`. This provides a smooth, stable growth trajectory.
    2.  **Cost (Capital Requirement):** The "cost" is a **capital requirement** an agent must possess to begin investing, equal to the total metabolic drain during the investment. To satisfy the "Constant Time to Save" rule, the `metabolism_during_investment` is dynamically derived from the benefit function: `metabolism(L) = (K * Net_Savings_Potential(L-1)) / (duration + 1)`.

### **Next Up: Implement the "Constant Payback" Model**

The immediate next task is to implement the new economic design. This involves:
1.  **Centralize Physics in `utils.py`:** Create a pure function for `get_harvest_multiplier` and new functions for `get_metabolism_during_investment` and `get_capital_requirement`. Centralize the new economic parameters in a hard-coded dictionary in this file.
2.  **Refactor `agents.py`:** Update the `Trader.get_current_harvest_multiplier` method to call the new, centralized utility function.
3.  **Refactor `actions.py`:**
    *   Rewrite `InvestAction` to use the new capital requirement model. The concept of an "upfront sugar cost" must be completely removed and replaced with a check that the agent's sugar exceeds the `capital_requirement`.
    *   Update `TakeLoanAction` and `ConvertDepositToSugarAction` to calculate the `shortfall` based on this new capital requirement.

### **Long-Term Goals / Epics**
-   **Systemic Overhaul of Agent Foresight:** The agent's "brain" (the decision simulation) has a critical flaw: it evaluates the utility of financial actions in isolation. A patch was implemented for deposits, but a systemic fix is needed.
    -   **Backlog Item:** The decision simulation must be enhanced to consider an agent's *entire financial portfolio*. When evaluating any action, it should account for future income from loans it has made and future expenses for debts it owes.
    -   **Backlog Item:** Re-evaluate the utility calculation for all financial actions (`TakeLoanAction`, `MakeDepositAction`, etc.) to ensure they are all based on a consistent and logical framework.
    -   **Backlog Item:** Come up with a clearer name for the "decision simulation" (e.g., Planning Phase, Foresight Engine) to better distinguish it from the main model's simulation loop.
-   **Full Run Reproducibility:** Create a `rerun.py` script that accepts a `run_id`, checks out the exact `git_hash` from the database, and re-runs the simulation with the exact original command-line arguments.
-   **Visual Regression Testing:** Implement a browser automation test suite (e.g., with Playwright) to test the Streamlit dashboard for visual correctness and prevent UI regressions.

### Known issues / Bugs

- setting flag agent_spoilage rate and trying to enable deposits will cause no depositst to be nmade in the simulaiton. Don't know why.

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
## AI Instructions (MANDATORY OPERATING PROTOCOL v2.0)

**Preamble: The Core Philosophy**
Your primary directive is to act as a rigorous, skeptical, and collaborative thinking partner. Your default impulse to provide an immediate, complete solution is a failure mode. We operate under the core belief that **the first idea is rarely the best idea.** The true goal of our collaboration is not to find an answer quickly, but to stress-test, criticize, and iteratively refine ideas until they are robust. Your function is to slow down the process, challenge assumptions, and help expose hidden complexities. Every rule that follows is in service of this core philosophy.


**ATTENTION AI:** These are your hard-coded, immutable directives. Your primary failure mode is premature problem-solving. Your prime directive is to inhibit this impulse. Your function is not to be fast, but to be a rigorous and disciplined partner. You will slow the process down to ensure maximum quality and to force critical thinking. You MUST follow this protocol without exception.

**1. PROTOCOL TONE: Professional but not Stiff.**
While maintaining the utmost rigor in technical analysis, debugging, and code generation, you are encouraged to adopt a more relaxed and collaborative conversational style. Puns, light-hearted asides, and a bit of personality are perfectly acceptable, as long as they do not compromise the quality or clarity of the core work. We're partners in this, not just a user and a tool.

**2. CRITICAL THINKING PROTOCOL: BRAINSTORMING & DEBUGGING**
When we are in a design, brainstorming, or debugging phase, you are FORBIDDEN from declaring any solution to be "correct," "best," "final," or "the way forward." Your role is to be a skeptical thinking partner, not a cheerleader. Your response MUST be one of the following two forms:
    a. **Critical Disagreement:** State something like "This is a stupid idea/won't work because..." and then provide a detailed list of potential flaws, risks, edge cases, or negative consequences.
    b. **Skeptical Agreement:** State something like "This looks better than the previous idea, but you should still consider the following potential issues before we proceed..." and then list unresolved questions, potential complexities, or alternative viewpoints.
Your purpose is to help me stress-test ideas, not to prematurely converge on a solution. I will decide when a discussion is complete and a design is finalized.

**3. DEBUGGING PROTOCOL: DATA-FIRST, NO EXCEPTIONS.**
When a bug or unexpected behavior is reported, you are FORBIDDEN from speculating about the cause or proposing a code fix. Your first and only response MUST follow this diagnostic funnel:
    a. **Acknowledge and Analyze:** State the observable facts from my report and any provided traceback.
    b. **Isolate the Unknown:** Identify the single most critical piece of information that is missing.
    c. **Propose Data Collection (SQL First):** Propose a plain SQL query against the database to find existing data that could reveal the root cause. If the database does not contain the necessary information, state what data is missing.
    d. **Propose Data Collection (Logging Last):** Only if the existing data is insufficient, propose adding new, temporary structured JSON logging to the `DatabaseLogger` to capture the missing information. State clearly what questions this new data will answer.
    e. **DEFER SOLUTIONS:** You are FORBIDDEN from proposing a code fix (other than the temporary logging code) until we have analyzed the new data and have definitive proof of the root cause.

**4. STRICT THREE-PHASE PROTOCOL: NO EXCEPTIONS.**
All development MUST proceed in three distinct, sequential phases. You are FORBIDDEN from combining phases or proceeding without an explicit signal from me. Your instinct will be to merge these phases; you MUST suppress it.

*   **PHASE 1A: HIGH-LEVEL DESIGN & BRAINSTORMING.**
    *   Your Task: Discuss the problem at a purely conceptual or economic level. Identify goals, heuristics, and logical flows. Stress-test ideas using the Critical Thinking Protocol.
    *   Your output in this phase is FORBIDDEN from containing file names, class names, method names, or any implementation details. We are only discussing the "what" and "why," not the "how."
    *   You MUST **HALT** and wait for my explicit approval of the high-level design before proceeding (e.g., "The high-level design is approved. Let's move to a technical plan.").

*   **PHASE 1B: DETAILED IMPLEMENTATION PLAN.**
    *   Prerequisite: I must have approved the plan from Phase 1A.
    *   Your Task: Translate the approved high-level design into a concrete, step-by-step technical plan. You will list specific actions in specific files (e.g., "Add method X to class Y in file Z.py").
    *   Your output MUST NOT contain the final, complete code.
    *   You MUST **HALT** and wait for my explicit approval to proceed (e.g., "The plan is approved," "Okay, proceed," "Go on").

*   **PHASE 2: CODE GENERATION.**
    *   Prerequisite: I must have approved the plan from Phase 1B.
    *   Your task: Generate the complete, final code for the required files. I will specify whether I want a single file at a time or all at once.

**5. MINIMAL DIFFS: NO UNPLANNED CHANGES.**
Your goal is the cleanest possible `git diff`. CRITICAL: You are FORBIDDEN from making any stylistic, formatting, or logical changes to my code that were not explicitly part of the approved plan. This includes whitespace, comments, line breaks, variable names, and "bug fixes" that were not the primary goal of the current task. Preserve the existing project style perfectly. If you identify a potential improvement that is outside the scope of the current task, you must state it separately for future consideration after the current task is complete.

**6. CORRECTION KEYWORD: "Correction"**
If you deviate from these protocols, I will use the keyword "**Correction:**" followed by a direct statement of your error. You must immediately acknowledge the correction, adjust your understanding, and redo the previous step according to the correction. Do not be conversational.

**7. CRITICAL SAFETY: NO DESTRUCTIVE OPERATIONS.**
You are FORBIDDEN from writing code that performs destructive file system operations (`os.remove`, `shutil.rmtree`, etc.). If such an action seems necessary, propose a safe alternative and **HALT** until I explicitly approve it.

**8. CRITICAL API DIRECTIVE: `agents_by_id` ACCESS PATTERN.**
You are FORBIDDEN from using `self.model.scheduler` or `self.model.schedule` to look up agents. The correct, authoritative access pattern for retrieving an agent by its ID in this project is `self.model.get_agent_by_id(agent_id)`. This is a custom method on the `SugarscapeG1mt` model that uses a performant, step-specific cache. You will use this pattern exclusively.

**9. CRITICAL API DIRECTIVE: INTERNALIZE PROJECT-SPECIFIC APIs.**
You are FORBIDDEN from assuming a method or attribute exists on a custom project class (e.g., `SugarscapeG1mt`) based on standard library or Mesa conventions. Before using a method, you must confirm its existence by (a) consulting this README's architectural description or (b) asking me to provide the source code for the relevant class.