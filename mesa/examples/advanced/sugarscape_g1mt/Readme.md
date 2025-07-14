# Sugarscape with an Investment and Lending Mechanic

## Summary

This project is a heavily modified version of the Mesa Sugarscape example, designed to incrementally build a simulation of a financial economy. The original trading mechanics have been removed. Instead, this model serves as a foundation for exploring how financial systems can emerge from simple agent-based rules.

The model now features a single population of **Traders** who forage for sugar on a 2D landscape. The core economic choice for an agent is between **Foraging** for immediate survival and **Investing** for a long-term benefit. This has been extended with a **peer-to-peer lending market**, where agents who cannot afford to invest can seek loans from agents with a surplus of sugar.

The simulation's architecture is built on the principle of a **Central Ledger** for all financial agreements, ensuring a single source of truth and preventing data duplication errors. This provides a robust framework for adding more complex financial instruments in the future.

Key features of this simulation framework include:
-   **Peer-to-Peer Lending:** Agents can now borrow and lend sugar to facilitate investments, allowing for the emergence of a basic credit market.
-   **Centralized Contract Ledger:** All loans are recorded as `Contract` objects in a central book owned by the model, ensuring data integrity.
-   **Configurable Mechanics:** Both investing and the new lending market can be enabled or disabled via flags (`--investments-enabled`, `--lending-enabled`) for controlled, comparative experiments.
-   **Rational Economic Choice:** Agents evaluate a full menu of possible actions—foraging, self-funded investing, and loan-funded investing—and select the option that maximizes their utility based on look-ahead simulations.
-   **Rigorous Database Logging:** All simulation runs are logged to a SQLite database (`simulation_results.db`), recording run metadata, parameters, and step-by-step aggregate data, including the full state of the financial ledger at each step.
-   **Reproducibility:** The model requires a clean Git repository, ensuring all logged results are tied to a specific commit hash.
-   **Multi-Page Analysis Dashboard:** A powerful Streamlit dashboard provides multiple views for deep analysis of results.

## Key Concepts & Architecture

### Dynamic Investments

The investment system is designed to be flexible and extensible. All investment opportunities and portfolios are defined in `investments.json`. This file has two main sections:
1.  **`definitions`**: An object where every possible investment is defined exactly once with a unique key. This adheres to the DRY (Don't Repeat Yourself) principle.
2.  **`portfolios`**: An object where each portfolio is a named list of keys that reference the investments in the `definitions` section. The model can be configured at runtime to provide agents with a specific portfolio.

### Peer-to-Peer Lending & Central Ledger

The lending system is built on a "Dumb Data, Smart Agent" philosophy.

-   **The `Contract` Object:** All financial agreements are represented by a simple `Contract` data object (defined in `contracts.py`). This object holds the "facts" of an agreement (creditor, debtor, principal, term) but contains no complex behavioral logic.
-   **The Central Ledger:** The model owns a single, authoritative ledger of all contracts. This ledger is indexed for high-performance lookups, preventing data duplication and ensuring integrity. It serves as the single source of truth for all financial obligations.
-   **Agent-Based Rules:** All intelligence resides within the `Trader` agents. Their `step()` method contains the rules for how they interact with the ledger. This includes evaluating opportunities, deciding whether to seek a loan, polling potential lenders, and finalizing loan agreements.

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

The `run_batch.py` script is used for running one or more simulations without the GUI, with all results logged to the database.

*   **Command Structure:**
    ```bash
    python -m sugarscape_g1mt.run_batch [options]
    ```
*   **Example (Single Run with Lending):**
    ```bash
    python -m sugarscape_g1mt.run_batch --steps 1000 --run_group "Lending_Enabled_Run" --lending_enabled true --lender_vision 10
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
│   investments.json        # External definitions for all investment opportunities
│   investment.py           # Defines the InvestmentOpportunity & SimulatedAgent classes
│   contracts.py            # Defines the Contract data object
│
│   dashboard.py            # Main entry point for the Streamlit dashboard
│   analysis_helpers.py     # Data-querying functions for the dashboard
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

### **Active Sprint: Comprehensive Structural Refactoring**

The immediate priority is a refactoring sprint to centralize configuration and improve code modularity. This will not change the simulation's behavior but will make future development significantly easier and more robust.

*   **Step 1: Create `utils.py` and Move `Gini` & `get_distance`**
    *   **Action:** Create `sugarscape_g1mt/utils.py`. Move `Gini()` from `model.py` and `get_distance()` from `agents.py` into `utils.py`. Update the original files to import them.

*   **Step 2: Create `config.json` and `load_config` Utility**
    *   **Action:** Create `sugarscape_g1mt/config.json` to hold all default simulation parameters. Add a `load_config()` function to `utils.py` to read this file.

*   **Step 3: Refactor `run_batch.py` to Use `config.json`**
    *   **Action:** Remove the hard-coded `DEFAULT_PARAMS` dictionary in `run_batch.py` and replace it with a call to `utils.load_config()`.

*   **Step 4: Refactor `model.py` to Use `config.json`**
    *   **Action:** Simplify the `SugarscapeG1mt.__init__` signature. Inside `__init__`, load defaults from `config.json` and merge them with any arguments passed to the constructor.

*   **Step 5: Refactor `agents.py` with a Pipelined `step()` Method**
    *   **Action:** Rewrite the monolithic `Trader.step()` method into a high-level pipeline that calls a sequence of new, private helper methods (`_perform_housekeeping`, `_assess_opportunities`, `_choose_best_action`, `_execute_action`, `_update_lifecycle`).

### **Next Up: New Features (Post-Refactoring)**

-   **Implement Demand Deposits:** Introduce a new `ContractType` for demand deposits. This will allow agents to act as "banks," accepting deposits from others, and will allow depositors to "call" their funds back at will. This will be added incrementally using the new, clean `step()` pipeline structure.

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

**1. DEBUGGING PROTOCOL: DATA-FIRST, NO EXCEPTIONS.**
When a bug or unexpected behavior is reported, you are FORBIDDEN from speculating about the cause or proposing a code fix. Your first and only response MUST follow this diagnostic funnel:
    a. **Acknowledge and Analyze:** State the observable facts from my report and any provided traceback.
    b. **Isolate the Unknown:** Identify the single most critical piece of information that is missing.
    c. **Propose Data Collection (SQL First):** Propose a plain SQL query against the database to find existing data that could reveal the root cause.
    d. **Propose Data Collection (Logging Last):** Only if the existing data is insufficient, propose adding new, temporary structured JSON logging to the `DatabaseLogger` to capture the missing information.
    e. **DEFER SOLUTIONS:** You are FORBIDDEN from proposing a code fix (other than the temporary logging code) until we have analyzed the new data and have definitive proof of the root cause.

**2. STRICT TWO-PHASE PROTOCOL: NO EXCEPTIONS.**
All development MUST proceed in two distinct, sequential phases. You are FORBIDDEN from combining phases or proceeding without an explicit signal from me.

*   **PHASE 1: DESIGN & IMPLEMENTATION PLAN.**
    *   Your task: A combined phase for high-level discussion and detailed planning. Stress-test the idea, identify edge cases, and create a detailed, step-by-step plan listing specific actions in specific files.
    *   Your output MUST NOT contain the final, complete code.
    *   You MUST **HALT** and wait for my explicit approval to proceed (e.g., "The plan is approved," "Okay, proceed," "Go on").

*   **PHASE 2: CODE GENERATION.**
    *   Prerequisite: I must have approved the plan.
    *   Your task: Generate the complete, final code for the required files. I will specify whether I want a single file at a time or all at once.

**3. MINIMAL DIFFS: NO UNPLANNED CHANGES.**
Your goal is the cleanest possible `git diff`. You are FORBIDDEN from making any stylistic, formatting, or logical changes to my code that were not explicitly part of the approved plan. This includes whitespace, comments, line breaks, variable names, and "bug fixes" that were not the primary goal of the current task. Preserve the existing project style perfectly.

**4. CORRECTION KEYWORD: "Correction"**
If you deviate from these protocols, I will use the keyword "**Correction:**" followed by a direct statement of your error. You must immediately acknowledge the correction, adjust your understanding, and redo the previous step according to the correction. Do not be conversational.

**5. CRITICAL SAFETY: NO DESTRUCTIVE OPERATIONS.**
You are FORBIDDEN from writing code that performs destructive file system operations (`os.remove`, `shutil.rmtree`, etc.). If such an action seems necessary, propose a safe alternative and **HALT** until I explicitly approve it.

**6. CRITICAL API DIRECTIVE: `agents_by_id` ACCESS PATTERN.**
You are FORBIDDEN from using `self.model.scheduler` or `self.model.schedule` to look up agents. The correct, authoritative access pattern for retrieving an agent by its ID in this project is `self.model.get_agent_by_id(agent_id)`. This is a custom method on the `SugarscapeG1mt` model that uses a performant, step-specific cache. You will use this pattern exclusively.

**7. CRITICAL API DIRECTIVE: INTERNALIZE PROJECT-SPECIFIC APIs.**
You are FORBIDDEN from assuming a method or attribute exists on a custom project class (e.g., `SugarscapeG1mt`) based on standard library or Mesa conventions. Before using a method, you must confirm its existence by (a) consulting this README's architectural description or (b) asking me to provide the source code for the relevant class.