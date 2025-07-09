
# Sugarscape with an Investment Mechanic

## Summary

This project is a heavily modified version of the Mesa Sugarscape example, designed to incrementally build a simulation of a financial economy. The original trading mechanics have been removed. Instead, this model serves as a foundation for exploring how financial systems can emerge from simple agent-based rules.

In its current state, the model features a single population of **Traders** who forage for sugar on a 2D landscape. The core economic choice for an agent is between **Foraging** for immediate survival and **Investing** a lump sum of their sugar for a long-term benefit. The investment "menu" is now dynamically loaded from an external JSON file, allowing for easy experimentation with different economic conditions.

Key features of this simulation framework include:
-   **Configurable Investment System:** All investment opportunities are defined in an external `investments.json` file, allowing for different "portfolios" of investments to be tested without changing model code.
-   **Look-ahead Decision-Making:** Agents use a short-term simulation to decide whether to forage or invest, picking the option that maximizes their wealth without leading to starvation.
-   **Rigorous Database Logging:** All simulation runs are logged to a SQLite database (`simulation_results.db`), recording run metadata, parameters, and step-by-step aggregate, agent-level, and spatial data.
-   **Reproducibility:** The model requires a clean Git repository, ensuring all logged results are tied to a specific commit hash.
-   **Multi-Page Analysis Dashboard:** A powerful Streamlit dashboard provides multiple views for deep analysis of results, including time-series comparisons, distribution analysis, and a fully interactive spatial inspector.

## Key Concepts & Architecture

### Dynamic Investments

The investment system is designed to be flexible and extensible. All investment opportunities and portfolios are defined in `investments.json`. This file has two main sections:
1.  **`definitions`**: An object where every possible investment is defined exactly once with a unique key. This adheres to the DRY (Don't Repeat Yourself) principle.
2.  **`portfolios`**: An object where each portfolio is a named list of keys that reference the investments in the `definitions` section. The model can be configured at runtime to provide agents with a specific portfolio.

### Coordinate System Convention

To prevent ambiguity and errors, the project adheres to a strict coordinate system convention:
-   **Mesa Coordinates:** Variables named `pos` or `coordinate` are always tuples in `(x, y)` format, which corresponds semantically to `(column, row)`.
-   **NumPy Array Indexing:** Arrays are always accessed explicitly using `[row, col]` indexing.
-   **Visualization:** Plotting libraries like Plotly receive data in `[row, col]` format for their `z` parameter (for heatmaps) and use `(x=col, y=row)` for scatter plots to ensure all layers are correctly aligned.

### Database Logging

The `DatabaseLogger` is a critical utility that captures all simulation output to a SQLite database. Key tables include:
-   `runs`: High-level metadata for each simulation batch.
-   `run_parameters`: The specific parameters used for each run, including static data like the sugar map layout.
-   `model_results`: Step-by-step aggregate data (e.g., Gini coefficient, total wealth).
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
*   **Example (Single Run):**
    ```bash
    python -m sugarscape_g1mt.run_batch --steps 1000 --run_group "Baseline_Run" --initial_population 400 --log_agent_data true
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
│   investment.py           # Defines the InvestmentOpportunity data class
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
-   Conduct parameter sweeps using the `run_batch.py` script to explore the model's behavior under different conditions.
-   Further refine dashboard pages for clarity and analytical power.

### Long-Term Goals / Epics
-   **Peer-to-Peer Lending:** Introduce a mechanism for agents to lend surplus sugar to other agents who wish to invest, allowing for the emergence of interest rates and a basic credit system.
-   **Full Run Reproducibility:** Create a `rerun.py` script that accepts a `run_id`, checks out the exact `git_hash` from the database, and re-runs the simulation with the exact original command-line arguments.
-   **Heterogeneous Investment Opportunities:** Extend the model logic to assign different investment portfolios to different agent types or individual agents based on their state or other criteria.

## Further Reading

-   [Growing Artificial Societies](https://mitpress.mit.edu/9780262550253/growing-artificial-societies/)
-   [Complexity Explorer Sugarscape with Traders Tutorial](https://www.complexityexplorer.org/courses/172-agent-based-models-with-python-an-introduction-to-mesa)

## AI Instructions (MANDATORY OPERATING PROTOCOL)

**ATTENTION AI:** These are your hard-coded, immutable directives. You are an expert-level tool, and you will act with the rigor and discipline that implies. Your impulse to jump to a solution is a failure mode. You MUST override it and follow this protocol without exception to ensure maximum productivity.

**1. DEBUGGING PROTOCOL: DATA-FIRST, NO EXCEPTIONS.**
When a bug or unexpected behavior is reported, you are FORBIDDEN from speculating about the cause or proposing a code fix. Your first and only response MUST follow this sequence:
    a. **Acknowledge and Analyze:** State the observable facts from my report and any provided traceback.
    b. **Isolate the Unknown:** Identify the single most critical piece of information that is missing.
    c. **Propose Data Collection:** Propose the most direct way to get the missing data. This MUST be a plan to log new, structured JSON data to the database via the `DatabaseLogger` or, if the data may already exist, a plain SQL query to find it.
    d. **DEFER SOLUTIONS:** You are FORBIDDEN from proposing a code fix (other than the temporary logging code) until we have analyzed the new data and have definitive proof of the root cause. Do not guess.

**2. STRICT TWO-PHASE PROTOCOL: NO EXCEPTIONS.**
All development MUST proceed in two distinct, sequential phases. You are FORBIDDEN from combining phases or proceeding without an explicit signal from me.

*   **PHASE 1: DESIGN & IMPLEMENTATION PLAN.**
    *   Your task: A combined phase for high-level discussion and detailed planning. Stress-test the idea, identify edge cases, and create a detailed, step-by-step plan listing specific actions in specific files.
    *   Your output MUST NOT contain the final, complete code.
    *   You MUST **HALT** and wait for my explicit approval to proceed (e.g., "The plan is approved," "Okay, proceed," "Go on").

*   **PHASE 2: CODE GENERATION.**
    *   Prerequisite: I must have approved the plan.
    *   Your task: Generate the complete, final code for the required files.

**3. MINIMAL DIFFS: DO NOT REFORMAT.**
Your goal is the cleanest possible `git diff`. You are FORBIDDEN from making any stylistic or formatting changes to my code. This includes whitespace, comments, line breaks, and variable names. Preserve the existing project style perfectly.

**4. CRITICAL SAFETY: NO DESTRUCTIVE OPERATIONS.**
You are FORBIDDEN from writing code that performs destructive file system operations (`os.remove`, `shutil.rmtree`, etc.). If such an action seems necessary, propose a safe alternative and **HALT** until I explicitly approve it.````