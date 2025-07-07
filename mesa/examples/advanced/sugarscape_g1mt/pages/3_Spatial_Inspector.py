import sys
from pathlib import Path
import streamlit as st
import matplotlib.pyplot as plt
import argparse
import os
import time
import pandas as pd
import json

# This block adds the project root to the python path.
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from sugarscape_g1mt import analysis_helpers as h


DB_PATH = Path("sugarscape_g1mt/simulation_results.db")

st.set_page_config(layout="wide", page_title="Spatial Inspector")
st.title("Spatial Inspector")
st.markdown("View the 2D grid and agent locations for a single run at a specific time step.")

def render_spatial_view(agent_df, sugar_map, run_params):
    """Renders the spatial grid using Matplotlib."""
    width = int(run_params.get('width', 50))
    height = int(run_params.get('height', 50))
    
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Plot sugar distribution
    ax.imshow(sugar_map, cmap='Greens', interpolation='nearest', origin='lower', vmin=0, vmax=10)

    # Plot agents
    if not agent_df.empty:
        # --- Agent Categorization Logic ---
        # Ensure the 'completed_investments' column exists
        if 'completed_investments' not in agent_df.columns:
            agent_df['completed_investments'] = '[]'
        
        # Safely parse the JSON string for each agent
        agent_df['completed_list'] = agent_df['completed_investments'].apply(
            lambda x: json.loads(x) if isinstance(x, str) and x.startswith('[') else []
        )
        
        # Define categories based on agent state
        is_investing_mask = (agent_df['is_investing'] == 1)
        has_invested_mask = (agent_df['completed_list'].str.len() > 0)
        
        categories = [
            {
                "label": "Investing", "color": "blue", "marker": "s", "size": 40,
                "mask": is_investing_mask
            },
            {
                "label": "Post-Investment", "color": "purple", "marker": "P", "size": 50,
                "mask": ~is_investing_mask & has_invested_mask
            },
            {
                "label": "Foraging", "color": "red", "marker": "o", "size": 25,
                "mask": ~is_investing_mask & ~has_invested_mask
            },
        ]
        
        # Plot each category
        for cat in categories:
            subset = agent_df[cat["mask"]]
            if not subset.empty:
                ax.scatter(subset['pos_x'], subset['pos_y'], c=cat['color'], 
                           marker=cat['marker'], s=cat['size'], label=cat['label'])

    ax.set_xlim(-0.5, width - 0.5)
    ax.set_ylim(-0.5, height - 0.5)
    ax.set_xticks(range(width))
    ax.set_yticks(range(height))
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.grid(True, which='both', color='k', linewidth=0.5, alpha=0.2)
    ax.set_aspect('equal')
    
    # Place legend outside the plot area to prevent it from moving
    ax.legend(bbox_to_anchor=(1.04, 1), loc="upper left")
    
    return fig

def main(args):
    db_mod_time = os.path.getmtime(DB_PATH) if DB_PATH.exists() else 0

    st.sidebar.header("Controls")
    
    agent_data_runs = h.get_runs_with_agent_data(DB_PATH, args.limit, args.include_tests, db_mod_time)

    if agent_data_runs.empty:
        st.warning("No runs with agent-level data logging found.")
        return

    selected_run_display = st.sidebar.selectbox(
        "Select a run to inspect:",
        options=agent_data_runs['display'].tolist(),
        key="spatial_run_select"
    )

    if not selected_run_display:
        st.info("Select a run from the sidebar.")
        return
    
    run_id = int(agent_data_runs[agent_data_runs['display'] == selected_run_display]['run_id'].iloc[0])
    
    if st.session_state.get('loaded_run_id') != run_id:
        with st.spinner(f"Loading all data for Run {run_id}..."):
            st.session_state.full_agent_df = h.get_pivoted_agent_data_for_run(DB_PATH, run_id, db_mod_time)
            st.session_state.all_sugar_maps = h.get_all_spatial_layers_for_run(DB_PATH, run_id, 'sugar', db_mod_time)
            st.session_state.run_params = h.get_run_params(DB_PATH, run_id)
            st.session_state.loaded_run_id = run_id
            st.session_state.playing = False
            if not st.session_state.full_agent_df.empty:
                st.session_state.step = int(st.session_state.full_agent_df['step'].min())

    if 'full_agent_df' not in st.session_state or st.session_state.full_agent_df.empty:
        st.error(f"No agent data loaded for Run {run_id}.")
        return
        
    min_step = int(st.session_state.full_agent_df['step'].min())
    max_step = int(st.session_state.full_agent_df['step'].max())
    
    col1, col2, col3 = st.sidebar.columns(3)
    if col1.button("Play", use_container_width=True):
        st.session_state.playing = True
    if col2.button("Stop", use_container_width=True):
        st.session_state.playing = False
    if col3.button("Step", use_container_width=True):
        st.session_state.step = min(st.session_state.get('step', min_step) + 1, max_step)
        st.session_state.playing = False

    new_step = st.sidebar.slider(
        "Simulation Step", 
        min_value=min_step, 
        max_value=max_step, 
        value=st.session_state.get('step', min_step),
        step=1
    )
    if new_step != st.session_state.get('step', min_step):
        st.session_state.step = new_step
        st.session_state.playing = False
    
    current_step = st.session_state.get('step', min_step)
    agent_df = st.session_state.full_agent_df.query(f"step == {current_step}")
    sugar_map = st.session_state.all_sugar_maps.get(current_step)
    
    st.header(f"Spatial View for Run {run_id} at Step {current_step}")
    
    if sugar_map:
        fig = render_spatial_view(agent_df, sugar_map, st.session_state.run_params)
        st.pyplot(fig, use_container_width=False)
    else:
        st.warning("No sugar distribution data found for this step.")

    if st.session_state.get('playing', False):
        if current_step < max_step:
            st.session_state.step += 1
        else:
            st.session_state.step = min_step
        time.sleep(0.1)
        st.rerun()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of recent runs to show. 0 for all.")
    parser.add_argument("--include-tests", action="store_true", help="Include test runs.")
    try:
        args, _ = parser.parse_known_args()
        return args
    except SystemExit:
        return parser.parse_args([])

if __name__ == "__main__":
    cli_args = parse_args()
    main(cli_args)