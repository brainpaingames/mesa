import sys
from pathlib import Path
import streamlit as st
import matplotlib.pyplot as plt
import argparse
import os

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
        # Separate agents by investment status for different markers/colors
        foraging_agents = agent_df[agent_df['is_investing'] == 0]
        investing_agents = agent_df[agent_df['is_investing'] == 1]
        
        ax.scatter(foraging_agents['pos_x'], foraging_agents['pos_y'], c='red', marker='o', s=25, label='Foraging')
        ax.scatter(investing_agents['pos_x'], investing_agents['pos_y'], c='blue', marker='s', s=40, label='Investing')

    ax.set_xlim(-0.5, width - 0.5)
    ax.set_ylim(-0.5, height - 0.5)
    ax.set_xticks(range(width))
    ax.set_yticks(range(height))
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.grid(True, which='both', color='k', linewidth=0.5, alpha=0.2)
    ax.set_aspect('equal')
    if not agent_df.empty:
        ax.legend()
    
    return fig

def main(args):
    db_mod_time = os.path.getmtime(DB_PATH) if DB_PATH.exists() else 0

    st.sidebar.header("Controls")
    
    agent_data_runs = h.get_runs_with_agent_data(DB_PATH, args.limit, args.include_tests, db_mod_time)

    if agent_data_runs.empty:
        st.warning("No runs with agent-level data logging found. Please run a simulation with 'Log Agent-Level Data' enabled.")
        return

    # For this page, we only inspect one run at a time.
    selected_run_display = st.sidebar.selectbox(
        "Select a run to inspect:",
        options=agent_data_runs['display'].tolist(),
    )

    if not selected_run_display:
        st.info("Select a run from the sidebar.")
        return
    
    run_id = int(agent_data_runs[agent_data_runs['display'] == selected_run_display]['run_id'].iloc[0])
    
    min_step, max_step = h.get_step_range_for_run(DB_PATH, run_id)
    
    if min_step is None:
        st.error(f"Could not retrieve step range for Run {run_id}.")
        return

    selected_step = st.sidebar.slider(
        "Simulation Step", 
        min_value=min_step, 
        max_value=max_step, 
        value=min_step,
        step=1
    )
    
    # Fetch data for the selected step
    agent_df = h.get_agent_data_for_step(DB_PATH, run_id, selected_step)
    sugar_map = h.get_spatial_layer_for_step(DB_PATH, run_id, selected_step, 'sugar')
    run_params = h.get_run_params(DB_PATH, run_id)
    
    st.header(f"Spatial View for Run {run_id} at Step {selected_step}")
    
    if sugar_map is None:
        st.warning("No sugar distribution data found for this step.")
        st.info("Ensure the model was run with agent/spatial logging enabled and is a recent version.")
    else:
        fig = render_spatial_view(agent_df, sugar_map, run_params)
        st.pyplot(fig, use_container_width=False)

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