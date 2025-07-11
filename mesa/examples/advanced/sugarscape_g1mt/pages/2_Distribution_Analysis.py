import sys
from pathlib import Path

# This block adds the project root to the python path.
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import plotly.express as px
import os
import argparse
import time
import pandas as pd
from sugarscape_g1mt import analysis_helpers as h

# This path is relative to the root of the project where streamlit is run
DB_PATH = Path("sugarscape_g1mt/simulation_results.db")

st.set_page_config(layout="wide", page_title="Distribution Analysis")
st.title("Distribution Analysis")
st.markdown("Explore the distribution of agent attributes for a single simulation run over time.")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100, help="Number of recent runs to show. 0 for all.")
    parser.add_argument("--include-tests", action="store_true", help="Include test runs.")
    try:
        args, _ = parser.parse_known_args()
        return args
    except SystemExit:
        return parser.parse_args([])

def main(args):
    db_mod_time = os.path.getmtime(DB_PATH) if DB_PATH.exists() else 0

    st.sidebar.header("Controls")
    
    agent_data_runs = h.get_runs_with_agent_data(DB_PATH, args.limit, args.include_tests, db_mod_time)

    if agent_data_runs.empty:
        st.warning("No runs with agent-level data logging found. Please run a simulation with 'Log Agent-Level Data' enabled.")
        return

    selected_display_runs = st.sidebar.multiselect(
        "Select run(s) to analyze:",
        options=agent_data_runs['display'].tolist(),
    )

    if not selected_display_runs:
        st.info("Select one or more runs from the sidebar to see their distributions.")
        if 'processed_agent_data' in st.session_state:
            del st.session_state['processed_agent_data']
        return
        
    selected_ids = agent_data_runs[agent_data_runs['display'].isin(selected_display_runs)]['run_id'].tolist()
    
    if st.session_state.get('processed_run_ids') != selected_ids:
        with st.spinner("Loading and processing agent data..."):
            all_dfs = []
            for run_id in selected_ids:
                # Use the new, cached, pre-pivoted function
                df = h.get_pivoted_agent_data_for_run(DB_PATH, run_id, db_mod_time)
                if not df.empty:
                    all_dfs.append(df)
            
            if not all_dfs:
                st.warning(f"No agent data found for the selected runs.")
                if 'processed_agent_data' in st.session_state:
                    del st.session_state['processed_agent_data']
                return
            
            st.session_state.processed_agent_data = pd.concat(all_dfs, ignore_index=True)
            st.session_state.processed_run_ids = selected_ids
            st.session_state.playing = False # Reset playing state
            # When new data is loaded, reset step to the new minimum
            if not st.session_state.processed_agent_data.empty:
                st.session_state.step = int(st.session_state.processed_agent_data['step'].min())
    
    if 'processed_agent_data' not in st.session_state or st.session_state.processed_agent_data.empty:
        st.error("No data to display.")
        return

    agent_data = st.session_state.processed_agent_data
    min_step = int(agent_data['step'].min())
    max_step = int(agent_data['step'].max())

    # Initialize or validate step and playing state.
    if 'playing' not in st.session_state:
        st.session_state.playing = False
    current_step = st.session_state.get('step', min_step)
    if not (min_step <= current_step <= max_step):
        st.session_state.step = min_step
    
    col1, col2 = st.sidebar.columns(2)
    if col1.button("Play", use_container_width=True, key="play"):
        st.session_state.playing = True
    if col2.button("Stop", use_container_width=True, key="stop"):
        st.session_state.playing = False

    new_step = st.sidebar.slider(
        "Simulation Step", 
        min_value=min_step, 
        max_value=max_step, 
        step=10,
        value=st.session_state.get('step', min_step)
    )
    
    if new_step != st.session_state.get('step', min_step):
        st.session_state.step = new_step
        st.session_state.playing = False

    freeze_x_axis = st.sidebar.checkbox("Freeze X-axis scale", value=True)
    freeze_y_axis = st.sidebar.checkbox("Freeze Y-axis scale", value=False)
    
    y_range_manual = None
    if freeze_y_axis:
        y_col1, y_col2 = st.sidebar.columns(2)
        y_min = y_col1.number_input("Y-axis min", value=0, min_value=0, step=10)
        y_max = y_col2.number_input("Y-axis max", value=50, min_value=0, step=10)
        y_range_manual = [y_min, y_max]

    step_data = agent_data[agent_data['step'] == st.session_state.step]

    if step_data.empty:
        st.warning(f"No agent data available at step {st.session_state.step}.")
    else:
        st.markdown(f"### Distributions at Step `{st.session_state.step}`")
        
        exclude_cols = ['run_id', 'step', 'agent_id']
        available_attributes = [col for col in agent_data.columns if col not in exclude_cols]
        
        axis_ranges = {}
        if freeze_x_axis:
            for attr in available_attributes:
                min_val = agent_data[attr].min()
                max_val = agent_data[attr].max()
                axis_ranges[attr] = [min_val, max_val]
        
        default_attrs = [a for a in ['sugar', 'age'] if a in available_attributes]
        if not default_attrs and available_attributes:
            default_attrs = [available_attributes[0]]

        selected_attributes = st.multiselect(
            "Select attributes to visualize:",
            options=available_attributes,
            default=default_attrs
        )

        st.sidebar.subheader("Bin Widths")
        bin_widths = {}
        for attr in selected_attributes:
            default_width = 5 if attr == 'sugar' else 1
            bin_widths[attr] = st.sidebar.number_input(f"Bin width for {attr}", value=default_width, min_value=1, step=1)

        if selected_attributes:
            for attribute in selected_attributes:
                fig = px.histogram(
                    step_data, 
                    x=attribute, 
                    color="run_id",
                    barmode="group",
                    title=f"Distribution of Agent {attribute.replace('_', ' ').capitalize()} at Step {st.session_state.step}",
                )
                fig.update_traces(xbins=dict(size=bin_widths.get(attribute, 1)))
                
                if freeze_x_axis and attribute in axis_ranges:
                    fig.update_xaxes(range=axis_ranges[attribute])
                if freeze_y_axis and y_range_manual:
                    fig.update_yaxes(range=y_range_manual)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select one or more attributes to see their distributions.")

    if st.session_state.get('playing', False):
        if st.session_state.step < max_step:
            st.session_state.step = min(st.session_state.step + 10, max_step)
        else:
            st.session_state.step = min_step
        
        time.sleep(0.1)
        st.rerun()

if __name__ == "__main__":
    cli_args = parse_args()
    main(cli_args)