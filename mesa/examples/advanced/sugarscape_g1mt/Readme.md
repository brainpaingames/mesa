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

### Batch Experiments (Command-Line)

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

### End-to-End Tests

The `pytest` suite runs a full simulation and asserts that the results fall within plausible scientific ranges.

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
```

## Development Backlog

### Immediate / Short-Term Tasks
-   **Extensive Testing:** Rigorously test the new lending functionality under various parameter settings.
-   **New Test Cases:** Create new, targeted tests in the `pytest` suite to cover edge cases in the lending market (e.g., loan defaults, market saturation).
-   **Refine Opportunity Cost:** The agent's calculation for its reservation interest amount should use the utility of its best *non-borrowing* alternative as the baseline, not just the foraging utility.
-   **Refactor `get_potential_harvest`:** Consolidate the duplicated logic for this method from `agents.py` and `investment.py` into a single function.

### Long-Term Goals / Epics
-   **Heterogeneous Lenders:** Introduce logic for lenders to have different risk tolerances and reservation rates, creating a more dynamic market for loans.
-   **Demand Deposits:** Implement a new `ContractType` for demand deposits, where agents can store sugar with others for a small return, and withdraw it at will.
-   **Full Run Reproducibility:** Create a `rerun.py` script that accepts a `run_id`, checks out the exact `git_hash` from the database, and re-runs the simulation with the exact original command-line arguments.

---
## Using the DatabaseLogger

The `DatabaseLogger` is a powerful tool for logging simulation data and text messages to a SQLite database. It is designed to be thread-safe by creating a new connection for each transaction. It is useful for debugging complex agent behaviors by recording their internal decision-making processes.

### Key Features

- **Thread-Safe:** Creates a new connection for each transaction, making it safe for multi-threaded applications.
- **Standard Logging Levels:** Supports `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL` levels.
- **Structured JSON Logging:** The core philosophy is to log parseable JSON strings to the `message` column of the `logs` table. This leverages SQLite's powerful JSON query capabilities for efficient analysis and debugging, avoiding the need to parse raw text.

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
    # We use json.dumps() to serialize the dictionary to a string.
    # We use the DEBUG level for this kind of verbose, internal data.
    self.model.db_logger.debug(self.model.run_id, json.dumps(decision_log))

    # ... rest of agent logic ...
```

By adhering to this pattern, you create a rich, queryable dataset in the `logs` table that is invaluable for tracing bugs and understanding emergent model behavior without needing to run an interactive debugger.