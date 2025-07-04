import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path

# --- Configuration ---
# This path is relative to the root of the project where streamlit is run
DB_PATH = Path("sugarscape_g1mt/simulation_results.db")

# --- Data Loading Functions with Caching ---

@st.cache_data
def get_all_runs(limit: int, include_tests: bool, _db_mod_time: float):
    """
    Connects to the DB and fetches a list of all runs.
    The _db_mod_time parameter is a dummy argument to bust the cache.
    """
    if not DB_PATH.exists():
        st.error(f"Database not found at {DB_PATH}. Please run a simulation first.")
        return pd.DataFrame()

    try:
        with sqlite3.connect(DB_PATH) as conn:
            base_query = "SELECT run_id, run_group, description FROM runs"
            params = []
            
            if not include_tests:
                base_query += " WHERE run_group NOT LIKE 'E2E_Test_%'"
            
            base_query += " ORDER BY run_id DESC"
            
            if limit > 0:
                base_query += " LIMIT ?"
                params.append(limit)

            runs_df = pd.read_sql_query(base_query, conn, params=params)
        
        runs_df['display'] = runs_df['run_id'].astype(str) + ": " + runs_df['run_group'] + " - " + runs_df['description']
        return runs_df
    except Exception as e:
        st.error(f"Failed to query the database. Error: {e}")
        return pd.DataFrame()

@st.cache_data
def get_runs_with_agent_data(limit: int, include_tests: bool, _db_mod_time: float):
    """
    Connects to the DB and fetches a list of runs that have agent-level data.
    The _db_mod_time parameter is a dummy argument to bust the cache.
    """
    if not DB_PATH.exists():
        st.error(f"Database not found at {DB_PATH}. Please run a simulation first.")
        return pd.DataFrame()

    try:
        with sqlite3.connect(DB_PATH) as conn:
            query = """
                SELECT r.run_id, r.run_group, r.description
                FROM runs r
                JOIN run_parameters p ON r.run_id = p.run_id
                WHERE p.parameter_name = 'log_agent_data' AND p.parameter_value = '1'
            """
            params = []

            if not include_tests:
                query += " AND r.run_group NOT LIKE 'E2E_Test_%'"

            query += " ORDER BY r.run_id DESC"

            if limit > 0:
                query += " LIMIT ?"
                params.append(limit)
            
            runs_df = pd.read_sql_query(query, conn, params=params)

        if not runs_df.empty:
            runs_df['display'] = runs_df['run_id'].astype(str) + ": " + runs_df['run_group'] + " - " + runs_df['description']
        return runs_df

    except Exception as e:
        st.error(f"Failed to query the database. Error: {e}")
        return pd.DataFrame()

@st.cache_data
def get_model_data_for_runs(selected_run_ids: tuple, _db_mod_time: float):
    """
    Fetches and pivots time-series data for selected run_ids.
    The _db_mod_time parameter is a dummy argument to bust the cache.
    """
    if not selected_run_ids:
        return pd.DataFrame()

    with sqlite3.connect(DB_PATH) as conn:
        placeholders = ','.join('?' for _ in selected_run_ids)
        query = f"""
            SELECT run_id, step, reporter_name, reporter_value
            FROM model_results
            WHERE run_id IN ({placeholders})
        """
        df = pd.read_sql_query(query, conn, params=selected_run_ids)

    wide_df = df.pivot_table(index=['run_id', 'step'], columns='reporter_name', values='reporter_value').reset_index()
    return wide_df

@st.cache_data
def get_agent_data_for_run(run_id: int, _db_mod_time: float):
    """
    Fetches agent-level data for a single, selected run_id.
    The _db_mod_time parameter is a dummy argument to bust the cache.
    """
    if not run_id:
        return pd.DataFrame()
    
    with sqlite3.connect(DB_PATH) as conn:
        query = "SELECT * FROM agent_data WHERE run_id = ?"
        df = pd.read_sql_query(query, conn, params=(run_id,))

    if df.empty:
        return pd.DataFrame()

    wide_df = df.pivot_table(index=['run_id', 'step', 'agent_id'], columns='attribute_name', values='attribute_value').reset_index()
    return wide_df