import subprocess
import pytest
import sqlite3
import os
import datetime
import sys
from pathlib import Path

# Define paths relative to the test file's location
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "simulation_results.db"

@pytest.mark.e2e
def test_book_baseline_run():
    """
    Runs a full end-to-end test of the baseline model from the book.
    It executes run_batch.py as a subprocess with a unique, timestamped
    run_group, and then queries the database to assert that the final
    results are within plausible ranges.
    """
    # --- 1. Define Test Parameters with a Unique Run Group ---
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run_group_name = f"E2E_Test_Book_Baseline_{timestamp}"

    test_params = {
        "steps": "1000",
        "run_group": run_group_name,
        "replications": "1",
        "seed": "42",  # Use a fixed seed for reproducibility
        "initial_population": "400",
        "agent_re_spawn": "false",
        "metabolism": "[1,4]",
        "vision": "[1,6]",
        "endowment": "[5,25]",
        "age": "[10000, 10000]",
        "sugar_regrowth_rate": "10",
        "db": str(DB_PATH)
    }

    # --- 2. Execute the Simulation ---
    # Construct the command-line arguments for the subprocess
    # Use 'sys.executable' to ensure we use the same Python interpreter as pytest
    command = [sys.executable, "-m", "sugarscape_g1mt.run_batch"]
    for key, value in test_params.items():
        command.append(f"--{key}")
        command.append(str(value)) # Ensure all values are strings for subprocess

    # Run the script from the parent directory of the package
    # This allows Python to find the 'sugarscape_g1mt' module
    working_dir = PROJECT_ROOT.parent
    subprocess.run(command, check=True, cwd=working_dir)

    # --- 3. Connect to DB and Query Results ---
    # The database path is now correctly and consistently defined by DB_PATH
    assert os.path.exists(DB_PATH), f"Database file not found at {DB_PATH}"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get the run_id for our unique test run
    cursor.execute("SELECT run_id FROM runs WHERE run_group = ?", (run_group_name,))
    run_id_result = cursor.fetchone()
    assert run_id_result is not None, f"No run found for unique group '{run_group_name}'"
    run_id = run_id_result[0]

    # Query for the specific final-step reporters for that run_id
    sql = """
        SELECT
            MAX(CASE WHEN reporter_name = 'Average Metabolism' THEN reporter_value END),
            MAX(CASE WHEN reporter_name = 'Gini' THEN reporter_value END),
            MAX(CASE WHEN reporter_name = '#Traders' THEN reporter_value END)
        FROM model_results
        WHERE run_id = ? AND step = ?
    """
    # A 1000-step run ends at step 999
    cursor.execute(sql, (run_id, 999))
    results = cursor.fetchone()
    conn.close()

    # --- 4. Assert a Plausible Outcome ---
    assert results is not None, f"Query for final step reporters returned no data for run_id {run_id}."

    avg_metabolism, gini, trader_count = results

    assert 1.0 <= avg_metabolism <= 2.5, f"Average metabolism ({avg_metabolism}) out of range [1.5, 2.5]"
    assert 0.30 <= gini <= 0.60, f"Gini ({gini}) out of range [0.30, 0.60]"
    assert 200 <= trader_count <= 350, f"Final trader count ({trader_count}) out of range [200, 350]"

@pytest.mark.e2e
def test_agent_data_and_aging():
    """
    Tests aging mechanic and agent data logging in a single, efficient run.
    - Checks that agents die of old age as expected.
    - Checks that agent data is logged without data type errors (no BLOBs).
    - Checks that dead agents are handled correctly (no position data).
    """
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run_group_name = f"E2E_Test_Aging_Data_{timestamp}"
    final_step = 14 # 15 steps means final step is 14

    test_params = {
        "steps": "15",
        "run_group": run_group_name,
        "seed": "1",
        "initial_population": "10",
        "agent_re_spawn": "false",
        "endowment": "[1000, 1000]", # Prevent starvation
        "age": "[10, 10]", # All agents die after step 10
        "log_agent_data": "true",
        "db": str(DB_PATH)
    }

    command = [sys.executable, "-m", "sugarscape_g1mt.run_batch"]
    for key, value in test_params.items():
        command.append(f"--{key}"); command.append(str(value))
    
    working_dir = PROJECT_ROOT.parent
    subprocess.run(command, check=True, cwd=working_dir)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get the run_id
    cursor.execute("SELECT run_id FROM runs WHERE run_group = ?", (run_group_name,))
    run_id = cursor.fetchone()[0]

    # 1. Assert agents died of old age
    cursor.execute("SELECT reporter_value FROM model_results WHERE run_id = ? AND step = ? AND reporter_name = '#Traders'", (run_id, final_step))
    final_population = cursor.fetchone()[0]
    assert final_population == 0, f"Expected 0 agents at end, but found {final_population}"

    # 2. Assert data integrity (no BLOBs) by performing an aggregation
    try:
        cursor.execute("SELECT AVG(attribute_value) FROM agent_data WHERE run_id = ? AND attribute_name = 'sugar'", (run_id,))
        avg_sugar = cursor.fetchone()[0]
        assert isinstance(avg_sugar, float)
    except sqlite3.OperationalError as e:
        pytest.fail(f"Aggregation on agent_data failed, indicating data type issue (BLOBs?): {e}")

    # 3. Assert correct logging for a dead agent
    # Agent 1 exists at step 9
    cursor.execute("SELECT 1 FROM agent_data WHERE run_id = ? AND step = 9 AND agent_id = 1 AND attribute_name = 'pos_x'", (run_id,))
    assert cursor.fetchone() is not None, "Agent 1 should have position data at step 9"
    # Agent 1 has died by step 11
    cursor.execute("SELECT 1 FROM agent_data WHERE run_id = ? AND step = 11 AND agent_id = 1 AND attribute_name = 'pos_x'", (run_id,))
    assert cursor.fetchone() is None, "Agent 1 should NOT have position data at step 11"
    
    conn.close()