import sys
from pathlib import Path

# This block adds the project root to the python path.
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
import plotly.express as px
import argparse
import os
from sugarscape_g1mt import analysis_helpers as h

# This path is relative to the root of the project where streamlit is run
DB_PATH = Path("sugarscape_g1mt/simulation_results.db")

st.set_page_config(layout="wide", page_title="Time Series Analysis")
st.title("Time Series Analysis")
st.markdown("Compare model-level reporters across multiple simulation runs.")

def parse_args():
    parser = argparse.ArgumentParser(description="An interactive analysis app for Sugarscape simulation results.")
    parser.add_argument("--limit", type=int, default=100, help="Number of recent runs to show. 0 for all.")
    parser.add_argument("--include-tests", action="store_true", help="Include test runs in the dropdown list.")
    try:
        args, _ = parser.parse_known_args()
        return args
    except SystemExit:
        return parser.parse_args([])

def main(args):
    db_mod_time = os.path.getmtime(DB_PATH) if DB_PATH.exists() else 0

    st.sidebar.header("Controls")
    
    all_runs_df = h.get_all_runs(DB_PATH, args.limit, args.include_tests, db_mod_time)

    if all_runs_df.empty:
        st.warning("No simulation runs found in the database.")
        return

    selected_display_runs = st.sidebar.multiselect(
        "Select Runs to Display:",
        options=all_runs_df['display'].tolist(),
    )

    if not selected_display_runs:
        st.info("Select one or more runs from the sidebar to see the results.")
        return

    selected_ids = all_runs_df[all_runs_df['display'].isin(selected_display_runs)]['run_id'].tolist()
    
    run_data_raw = h.get_model_data_for_runs(DB_PATH, tuple(selected_ids), db_mod_time)

    if run_data_raw.empty:
        st.warning("No model-level data found for the selected runs.")
        return

    # --- START: New Code ---
    # Merge the descriptive 'display' name into the data DataFrame for plotting.
    run_display_names = all_runs_df[['run_id', 'display']]
    run_data = pd.merge(run_data_raw, run_display_names, on='run_id', how='inner')
    # --- END: New Code ---

    available_reporters = [col for col in run_data.columns if col not in ['run_id', 'step', 'display']]
    
    default_reporters = [rep for rep in ["Harvested Sugar", "Gini"] if rep in available_reporters]

    selected_reporters = st.sidebar.multiselect(
        "Select Reporters to Plot:",
        options=available_reporters,
        default=default_reporters
    )

    if selected_reporters:
        for reporter in selected_reporters:
            st.subheader(f"Plot for: {reporter}")
            # --- START: Modified Code ---
            # Use the 'display' column for the color legend and customize the legend title.
            fig = px.line(
                run_data, 
                x="step", 
                y=reporter, 
                color="display",  # Changed from "run_id"
                title=f"{reporter} over Time",
                labels={'display': 'Run'} # Cleaner legend title
            )
            # --- END: Modified Code ---
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Please select at least one reporter to plot.")

if __name__ == "__main__":
    cli_args = parse_args()
    main(cli_args)