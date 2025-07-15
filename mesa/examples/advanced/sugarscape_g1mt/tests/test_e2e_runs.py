import subprocess
import pytest
import sqlite3
import os
import datetime
import sys
from pathlib import Path
import pandas as pd

# The import path is now handled by the conftest.py file.
from sugarscape_g1mt import analysis_helpers as h


# Define paths relative to the test file's location
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "simulation_results.db"

@pytest.mark.e2e
def test_smoke_and_aging():
    """
    A fast test that (a) proves the model can run (smoke test), and (b)
    verifies the aging mechanic and data logging integrity.
    """
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run_group_name = f"E2E_Test_Smoke_Aging_{timestamp}"
    final_step = 14 # 15 steps means final step is 14

    test_params = {
        "total_steps": "15",
        "run_group": run_group_name,
        "replications": "1",
        "seed": "1",
        "initial_population": "10",
        "agent_re_spawn": "false",
        "endowment": "[1000, 1000]", # Prevent starvation
        "age": "[10, 10]", # All agents die after step 10
        "log_agent_data": "true",
        "lending_enabled": "false",
        "investments_enabled": "false",
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


@pytest.mark.e2e
def test_lending_investment_and_helpers():
    """
    A comprehensive test of the financial mechanics AND the analysis helper
    functions using real output from the simulation.
    """
    # --- 1. Define and Execute the Simulation ---
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run_group_name = f"E2E_Test_Lending_Investment_{timestamp}"

    test_params = {
        "total_steps": "100",
        "run_group": run_group_name,
        "replications": "1",
        "seed": "42",
        "initial_population": "100",
        "agent_re_spawn": "false",
        "endowment": "[5, 5]", # Low endowment to force loan demand
        "age": "[1000, 1000]", # Prevent deaths by old age
        "log_agent_data": "true",
        "lending_enabled": "true",
        "investments_enabled": "true",
        "db": str(DB_PATH)
    }

    command = [sys.executable, "-m", "sugarscape_g1mt.run_batch"]
    for key, value in test_params.items():
        command.append(f"--{key}")
        command.append(str(value))

    working_dir = PROJECT_ROOT.parent
    subprocess.run(command, check=True, cwd=working_dir)

    # --- 2. Assert Economic Outcomes ---
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get the run_id
    cursor.execute("SELECT run_id FROM runs WHERE run_group = ?", (run_group_name,))
    run_id_result = cursor.fetchone()
    assert run_id_result is not None, "Failed to find the test run in the database."
    run_id = run_id_result[0]

    # Assert that at least one loan was active at some point during the run
    cursor.execute("""
        SELECT SUM(reporter_value)
        FROM model_results
        WHERE run_id = ? AND reporter_name = 'Active Loan Count'
    """, (run_id,))
    total_active_loans_over_time = cursor.fetchone()[0]
    assert total_active_loans_over_time is not None and total_active_loans_over_time > 0, \
        "No active loans were ever recorded during the simulation."

    conn.close()

    # --- 3. Assert Data Helper Functionality ---
    # Use the live DB path and the run_id we just created
    # The _db_mod_time is a dummy value to ensure the cache runs
    df_from_helper = h.get_model_data_for_runs(DB_PATH, (run_id,), 0)

    # Assert that the function did not crash and returned a DataFrame
    assert isinstance(df_from_helper, pd.DataFrame), "get_model_data_for_runs did not return a DataFrame."
    assert not df_from_helper.empty, "get_model_data_for_runs returned an empty DataFrame."

    # Assert that the non-numeric 'Ledger' column was successfully filtered out
    assert 'Ledger' not in df_from_helper.columns, "The 'Ledger' column should have been filtered out by the helper."

    # Assert that expected numeric columns are still present
    assert '#Traders' in df_from_helper.columns, "Expected numeric column '#Traders' is missing."
    assert 'Gini' in df_from_helper.columns, "Expected numeric column 'Gini' is missing."


@pytest.mark.e2e
def test_flags_disable_features():
    """
    Tests that setting 'lending_enabled' and 'investments_enabled' to false
    correctly disables those features in the simulation.
    """
    # --- Scenario 1: Test with Lending Disabled ---
    timestamp1 = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run_group_lending_off = f"E2E_Test_Lending_Disabled_{timestamp1}"

    params_lending_off = {
        "total_steps": "50", "run_group": run_group_lending_off, "seed": "123",
        "initial_population": "50", "endowment": "[5, 5]", "age": "[1000, 1000]",
        "investments_enabled": "true", # Investments ON
        "lending_enabled": "false",    # Lending OFF
        "db": str(DB_PATH)
    }
    
    command = [sys.executable, "-m", "sugarscape_g1mt.run_batch"]
    for key, value in params_lending_off.items():
        command.append(f"--{key}"); command.append(str(value))
    
    working_dir = PROJECT_ROOT.parent
    subprocess.run(command, check=True, cwd=working_dir)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT run_id FROM runs WHERE run_group = ?", (run_group_lending_off,))
    run_id1 = cursor.fetchone()[0]

    # Assert that NO loans were created
    cursor.execute("SELECT SUM(reporter_value) FROM model_results WHERE run_id = ? AND reporter_name = 'Active Loan Count'", (run_id1,))
    total_loans = cursor.fetchone()[0]
    # The sum could be None if no rows are returned, or 0. Both are valid.
    assert total_loans is None or total_loans == 0, "Loans were created even when lending was disabled."

    # --- Scenario 2: Test with Investments Disabled ---
    timestamp2 = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run_group_invest_off = f"E2E_Test_Investments_Disabled_{timestamp2}"

    params_invest_off = {
        "total_steps": "50", "run_group": run_group_invest_off, "seed": "123",
        "initial_population": "50", "endowment": "[5, 5]", "age": "[1000, 1000]",
        "log_agent_data": "true",
        "investments_enabled": "false", # Investments OFF
        "lending_enabled": "true",     # Lending ON (but should have no effect)
        "db": str(DB_PATH)
    }

    command = [sys.executable, "-m", "sugarscape_g1mt.run_batch"]
    for key, value in params_invest_off.items():
        command.append(f"--{key}"); command.append(str(value))
    
    subprocess.run(command, check=True, cwd=working_dir)

    cursor.execute("SELECT run_id FROM runs WHERE run_group = ?", (run_group_invest_off,))
    run_id2 = cursor.fetchone()[0]

    # Assert that NO agent ever entered the 'is_investing' state
    cursor.execute("SELECT SUM(attribute_value) FROM agent_data WHERE run_id = ? AND attribute_name = 'is_investing'", (run_id2,))
    total_investing_time = cursor.fetchone()[0]
    assert total_investing_time is None or total_investing_time == 0, "Agents were investing even when investments were disabled."

    conn.close()

# sugarscape_g1mt/tests/test_e2e_runs.py

# ... (keep all existing code in the file) ...

@pytest.mark.e2e
def test_deposits_and_calls():
    """
    Tests that the demand deposit functionality is working correctly by
    running a simulation and checking for deposit creation.
    """
    # --- 1. Define and Execute the Simulation ---
    # We use the same rich economic scenario as the lending/investment test,
    # but with deposits enabled.
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run_group_name = f"E2E_Test_Deposits_{timestamp}"

    test_params = {
        "total_steps": "100",
        "run_group": run_group_name,
        "replications": "1",
        "seed": "42",
        "initial_population": "100",
        "agent_re_spawn": "false",
        "endowment": "[5, 5]", # Low endowment to force financial activity
        "age": "[1000, 1000]", # Prevent deaths by old age
        "log_agent_data": "false", # Keep it fast for this test
        "lending_enabled": "true",
        "investments_enabled": "true",
        "deposits_enabled": "true", # The key feature to test
        "db": str(DB_PATH)
    }

    command = [sys.executable, "-m", "sugarscape_g1mt.run_batch"]
    for key, value in test_params.items():
        command.append(f"--{key}")
        command.append(str(value))

    working_dir = PROJECT_ROOT.parent
    subprocess.run(command, check=True, cwd=working_dir)

    # --- 2. Assert Economic Outcomes ---
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get the run_id
    cursor.execute("SELECT run_id FROM runs WHERE run_group = ?", (run_group_name,))
    run_id_result = cursor.fetchone()
    assert run_id_result is not None, "Failed to find the test run in the database."
    run_id = run_id_result[0]

    # Assertion 1: Check that deposits were actually created.
    cursor.execute("""
        SELECT SUM(reporter_value)
        FROM model_results
        WHERE run_id = ? AND reporter_name = 'Active Deposit Count'
    """, (run_id,))
    total_active_deposits_over_time = cursor.fetchone()[0]
    assert total_active_deposits_over_time is not None and total_active_deposits_over_time > 0, \
        "No active deposits were ever recorded during the simulation."

    # Assertion 2: Check the ledger for a valid deposit contract structure.
    cursor.execute("""
        SELECT reporter_value FROM model_results
        WHERE run_id = ? AND reporter_name = 'Ledger'
        ORDER BY step DESC LIMIT 1
    """, (run_id,))
    final_ledger_json = cursor.fetchone()[0]
    final_ledger = json.loads(final_ledger_json)

    deposit_found_in_ledger = False
    for contract_id, contract_data in final_ledger.items():
        if contract_data.get("contract_type") == "DEMAND_DEPOSIT":
            deposit_found_in_ledger = True
            assert "current_principal" in contract_data, \
                f"Demand deposit contract {contract_id} is missing 'current_principal' field."
            break # Found one, no need to check further
    
    assert deposit_found_in_ledger, "No demand deposit contracts found in the final ledger."

    conn.close()