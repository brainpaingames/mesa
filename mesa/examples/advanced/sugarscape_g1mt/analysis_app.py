import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from pathlib import Path
import argparse
import os

# --- Configuration ---
# Correct the path to be relative to the execution directory (advanced/)
DB_PATH = Path("sugarscape_g1mt/simulation_results.db")
st.set_page_config(layout="wide")
st.title("Sugarscape Simulation Results Explorer")

# --- Data Loading Functions with Caching ---

@st.cache_data
def get_all_runs(db_path: Path, limit: int, include_tests: bool, _db_mod_time: float):
    """
    Connects to the DB and fetches a list of runs.
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
                # Exclude runs where the group name starts with our test prefix
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
def get_data_for_runs(db_path: Path, selected_run_ids: tuple, _db_mod_time: float):
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

def main(args):
    """Main function to run the Streamlit app."""
    # Use the globally defined DB_PATH for consistency
    db_path = DB_PATH
    
    # Get the database modification time to use as a cache key
    db_mod_time = os.path.getmtime(db_path) if db_path.exists() else 0

    # --- Sidebar for User Selections ---
    st.sidebar.header("Selections")
    
    all_runs_df = get_all_runs(db_path, args.limit, args.include_tests, db_mod_time)

    if not all_runs_df.empty:
        selected_display_runs = st.sidebar.multiselect(
            "Select Runs to Display:",
            options=all_runs_df['display'].tolist(),
        )

        selected_ids = all_runs_df[all_runs_df['display'].isin(selected_display_runs)]['run_id'].tolist()
        
        run_data = get_data_for_runs(db_path, tuple(selected_ids), db_mod_time)

        if not run_data.empty:
            available_reporters = [col for col in run_data.columns if col not in ['run_id', 'step']]
            
            selected_reporters = st.sidebar.multiselect(
                "Select Reporters to Plot:",
                options=available_reporters,
                default=available_reporters[:2]
            )

            # --- Main Panel for Plots ---
            if selected_reporters:
                for reporter in selected_reporters:
                    st.subheader(f"Plot for: {reporter}")
                    fig = px.line(run_data, x="step", y=reporter, color="run_id", title=f"{reporter} over Time")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Please select at least one reporter to plot.")
        else:
            st.info("Select one or more runs from the sidebar to see the results.")
    else:
        st.warning("No simulation runs found in the database matching your criteria.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="An interactive analysis app for Sugarscape simulation results.")
    # We remove the --db argument as the path is now fixed and consistent
    parser.add_argument("--limit", type=int, default=20, help="Number of recent runs to show in the dropdown. 0 for all.")
    parser.add_argument("--include-tests", action="store_true", help="Include test runs in the dropdown list.")
    
    try:
        cli_args = parser.parse_args()
    except SystemExit as e:
        pass
    else:
        main(cli_args)