That is a fantastic idea. Using the `README.md` as a living document and a "state dump" for our sessions is an excellent practice. It formalizes our process, ensures the project is well-documented, and provides a perfect starting point for any future session. I agree completely.

Based on the file tree you provided and the recap of our recent work, here is a comprehensively updated `README.md`. It integrates the information I was going to provide for the next session directly into the project's documentation.

---

### Updated `Readme.md`

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
-   The **Spatial Inspector** page features a sophisticated **Plotly** chart that overlays a heatmap, contour lines, and agent markers. It uses a dedicated transparent top layer to provide detailed hover tooltips for every cell on the grid.

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
    python -m sugarscape_g1mt.run_batch --steps 1000 --run_group "Baseline_Run" --initial_population 400 
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