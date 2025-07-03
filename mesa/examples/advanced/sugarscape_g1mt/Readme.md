

# Sugarscape with an Investment Mechanic

## Summary

This project is a heavily modified version of the Mesa Sugarscape example, designed to incrementally build a simulation of a financial economy. The original trading and spice mechanics have been removed. Instead, this model serves as a foundation for exploring how financial systems can emerge from simple agent-based rules.

In its current state, the model features a single population of **Traders** who forage for sugar on a 2D landscape. The core economic choice for an agent is between **Foraging** for immediate survival and **Investing** a lump sum of their sugar for a long-term benefit—a permanent reduction in their metabolic rate.

Key features of this simulation framework include:
-   **Look-ahead Decision-Making:** Agents use a short-term simulation to decide whether to forage or invest, picking the option that maximizes their wealth without leading to starvation.
-   **Rigorous Database Logging:** All simulation runs are logged to a SQLite database (`simulation_results.db`), recording run metadata, parameters, and step-by-step aggregate and agent-level data.
-   **Reproducibility:** In its default mode, the model requires a clean Git repository, ensuring all logged results are tied to a specific commit hash.
-   **Developer Mode:** A `--mesa-dev` flag allows for rapid, iterative testing by bypassing all database logging and Git checks.
-   **Batch Execution & Testing:** The project includes a powerful command-line script (`run_batch.py`) for running parameter sweeps and a `pytest` suite for automated end-to-end testing of the model's scientific output.

## Agent: The `Trader`

The model consists of a single agent type, the `Trader`, which has the following attributes:
-   A store of **sugar**, which is its wealth and lifeblood.
-   A **metabolism**, which determines how much sugar it consumes each step.
-   A **vision**, which determines how far it can see to find new sugar patches.

Each turn, a `Trader` can perform one of two main actions:
1.  **Forage:** Move to the best available empty cell within its vision and harvest all the sugar on that patch.
2.  **Invest:** If it has sufficient sugar, it can pay a significant upfront cost and become inactive for a set duration. Upon completion, its metabolism is permanently reduced, making it more efficient for the rest of its life.

## How to Run

**Important:** All commands should be run from the parent directory (`.../mesa/examples/advanced/`).

### Interactive App (GUI)

The interactive app allows you to visualize the simulation and adjust parameters on the fly.

**1. Launch in Standard Mode:**

*   **Windows (PowerShell):**
    ```powershell
    $env:PYTHONPATH='.'; solara run sugarscape_g1mt.app
    ```
*   **Windows (CMD):**
    ```batch
    set PYTHONPATH=. & solara run sugarscape_g1mt.app
    ```
*   **Linux / macOS:**
    ```bash
    PYTHONPATH=. solara run sugarscape_g1mt.app
    ```

**2. Launch in Developer Mode:**
(Bypasses database logging and Git checks)

*   **Windows (PowerShell):**
    ```powershell
    $env:PYTHONPATH='.'; solara run sugarscape_g1mt.app -- --mesa-dev
    ```
*   **Windows (CMD):**
    ```batch
    set PYTHONPATH=. & solara run sugarscape_g1mt.app -- --mesa-dev
    ```
*   **Linux / macOS:**
    ```bash
    PYTHONPATH=. solara run sugarscape_g1mt.app -- --mesa-dev
    ```

### Batch Experiments (Command-Line)

The `run_batch.py` script is used for running one or more simulations without the GUI, with all results logged to the database.

*   **Command Structure:**
    ```bash
    python -m sugarscape_g1mt.run_batch [options]
    ```
*   **Example (Single Run with Custom Parameters):**
    ```bash
    python -m sugarscape_g1mt.run_batch --steps 1000 --run_group "Book_Baseline_Run" --initial_population 400 --agent_re_spawn false --metabolism "[1,4]" --vision "[1,6]" --endowment "[5,25]"
    ```
*   **Example (Parameter Sweep):**
    ```bash
    python -m sugarscape_g1mt.run_batch --replications 3 --initial_population "[250, 350]" --endowment "[[6,6], [10,20]]"
    ```

### Analysis & Visualization App

The Streamlit app allows you to interactively explore and plot the results from the simulation database.

*   **Base Command:**
    ```bash
    streamlit run sugarscape_g1mt/analysis_app.py
    ```
*   **Example (With Options):**
    ```bash
    streamlit run sugarscape_g1mt/analysis_app.py -- --limit 50 --include-tests
    ```

### End-to-End Tests

The `pytest` suite runs a full simulation and asserts that the results fall within plausible scientific ranges. This is used to validate the model's integrity after code changes.

*   **Command:**
    ```bash
    pytest sugarscape_g1mt
    ```

## Project Structure

*   `model.py`: The main `SugarscapeG1mt` model class that manages the grid and agents.
*   `agents.py`: Defines the `Trader` agent class and its logic.
*   `app.py`: Defines the interactive Solara web application.
*   `database_logger.py`: Contains the `DatabaseLogger` class for writing results to SQLite.
*   `run_batch.py`: Command-line script for running non-interactive experiments.
*   `analysis_app.py`: The Streamlit application for visualizing results.
*   `sugar_map.txt`: Provides the sugar landscape in a raster-type format.
*   `pytest.ini`: Configuration file for the test suite.
*   `tests/`: Directory containing all automated tests.
    *   `test_e2e_runs.py`: The end-to-end test that validates the baseline model run.

## Future Work

The next major milestone is to build upon this validated baseline by introducing peer-to-peer lending, allowing agents to earn returns on their surplus sugar. This will be the first step towards simulating a more complex financial system with emergent banking behavior.

## Further Reading

-   [Growing Artificial Societies](https://mitpress.mit.edu/9780262550253/growing-artificial-societies/)
-   [Complexity Explorer Sugarscape with Traders Tutorial](https://www.complexityexplorer.org/courses/172-agent-based-models-with-python-an-introduction-to-mesa)