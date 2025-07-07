import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import json

@st.cache_data
def get_all_runs(db_path: Path, limit: int, include_tests: bool, _db_mod_time: float):
    """
    Connects to the DB and fetches a list of all runs.
    The _db_mod_time parameter is a dummy argument to bust the cache.
    """
    if not db_path.exists():
        st.error(f"Database not found at {db_path}. Please run a simulation first.")
        return pd.DataFrame()

    try:
        with sqlite3.connect(db_path) as conn:
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
def get_runs_with_agent_data(db_path: Path, limit: int, include_tests: bool, _db_mod_time: float):
    """
    Connects to the DB and fetches a list of runs that have agent-level data.
    The _db_mod_time parameter is a dummy argument to bust the cache.
    """
    if not db_path.exists():
        st.error(f"Database not found at {db_path}. Please run a simulation first.")
        return pd.DataFrame()

    try:
        with sqlite3.connect(db_path) as conn:
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
def get_model_data_for_runs(db_path: Path, selected_run_ids: tuple, _db_mod_time: float):
    """
    Fetches and pivots time-series data for selected run_ids.
    The _db_mod_time parameter is a dummy argument to bust the cache.
    """
    if not selected_run_ids:
        return pd.DataFrame()

    with sqlite3.connect(db_path) as conn:
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
def get_agent_data_for_run(db_path: Path, run_id: int, _db_mod_time: float, _logger=None):
    """
    Fetches agent-level data for a single, selected run_id.
    The _db_mod_time and _logger parameters are ignored by the cache.
    """
    if _logger:
        _logger.debug(None, f"Attempting to fetch agent data for run_id: {run_id} from DB: {db_path.resolve()}")

    if not run_id:
        if _logger:
            _logger.warning(None, "get_agent_data_for_run called with no run_id.")
        return pd.DataFrame()
    
    try:
        with sqlite3.connect(db_path) as conn:
            query = "SELECT * FROM agent_data WHERE run_id = ?"
            df = pd.read_sql_query(query, conn, params=(run_id,))
        if _logger:
            _logger.debug(None, f"Query for run_id {run_id} returned a DataFrame with shape: {df.shape}")
        return df
    except Exception as e:
        if _logger:
            _logger.error(None, f"Error querying agent data for run_id {run_id}: {e}")
        st.error(f"Database query for agent data failed: {e}")
        return pd.DataFrame()

@st.cache_data
def get_run_params(db_path: Path, run_id: int):
    """
    Fetches the parameters for a given run_id.
    """
    with sqlite3.connect(db_path) as conn:
        query = "SELECT parameter_name, parameter_value FROM run_parameters WHERE run_id = ?"
        df = pd.read_sql_query(query, conn, params=(run_id,))
    return dict(zip(df['parameter_name'], df['parameter_value']))

def get_step_range_for_run(db_path: Path, run_id: int):
    """Gets the min and max step for a run with agent data."""
    with sqlite3.connect(db_path) as conn:
        query = "SELECT MIN(step), MAX(step) FROM agent_data WHERE run_id = ?"
        try:
            min_step, max_step = conn.execute(query, (run_id,)).fetchone()
        except Exception:
            min_step, max_step = None, None
    return min_step, max_step

def get_agent_data_for_step(db_path: Path, run_id: int, step: int):
    """Fetches and pivots agent data for a specific run and step."""
    with sqlite3.connect(db_path) as conn:
        query = "SELECT * FROM agent_data WHERE run_id = ? AND step = ?"
        df = pd.read_sql_query(query, conn, params=(run_id, step))
    if df.empty:
        return pd.DataFrame()
    return df.pivot_table(
        index='agent_id', 
        columns='attribute_name', 
        values='attribute_value'
    ).reset_index()

@st.cache_data
def get_spatial_layer_for_step(db_path: Path, run_id: int, step: int, layer_name: str):
    """Fetches a specific spatial layer for a given run and step."""
    with sqlite3.connect(db_path) as conn:
        query = "SELECT layer_data FROM spatial_data WHERE run_id = ? AND step = ? AND layer_name = ?"
        try:
            cursor = conn.cursor()
            result = cursor.execute(query, (run_id, step, layer_name)).fetchone()
            if result:
                return json.loads(result[0])
            else:
                return None
        except Exception as e:
            st.error(f"Error fetching spatial data: {e}")
            return None