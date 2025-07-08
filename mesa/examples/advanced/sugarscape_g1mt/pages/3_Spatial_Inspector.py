import sys
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go
import argparse
import os
import time
import pandas as pd
import json
import numpy as np

# This block adds the project root to the python path.
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from sugarscape_g1mt import analysis_helpers as h
from sugarscape_g1mt.database_logger import DatabaseLogger


DB_PATH = Path("sugarscape_g1mt/simulation_results.db")

st.set_page_config(layout="wide", page_title="Spatial Inspector")
st.title("Spatial Inspector")
st.markdown("View the 2D grid and agent locations for a single run at a specific time step.")

def render_spatial_view(db_logger, run_id, step, agent_df, sugar_map, run_params, static_sugar_map):
    """Renders the spatial grid using Plotly for interactivity."""
    width = int(run_params.get('width', 50))
    height = int(run_params.get('height', 50))
    
    # --- 1. Data Preparation ---
    sugar_map = np.array(sugar_map)
    static_sugar_map = np.array(static_sugar_map)

    x_coords, y_coords = np.meshgrid(np.arange(width), np.arange(height))
    grid_df = pd.DataFrame({'x': x_coords.flatten(), 'y': y_coords.flatten()})
    
    grid_df['current_sugar'] = sugar_map.flatten()
    grid_df['max_capacity'] = static_sugar_map.flatten()

    if not agent_df.empty:
        agent_df_unique = agent_df.drop_duplicates(subset=['pos_x', 'pos_y'], keep='first')
        merged_df = pd.merge(grid_df, agent_df_unique, how='left', left_on=['x', 'y'], right_on=['pos_x', 'pos_y'])
    else:
        merged_df = grid_df
        for col in ['agent_id', 'sugar', 'age', 'completed_investments', 'is_investing']:
            if col not in merged_df.columns:
                merged_df[col] = np.nan

    def create_hover_text(row):
        text = f"<b>Cell ({row['x']}, {row['y']})</b><br>"
        text += f"Current Sugar: {row['current_sugar']:.2f}<br>"
        text += f"Max Capacity: {row['max_capacity']:.2f}"
        if pd.notna(row['agent_id']):
            text += "<br><br><b>--- Occupying Agent ---</b>"
            text += f"<br>Agent ID: {int(row['agent_id'])}"
            text += f"<br>Agent Sugar: {row['sugar']:.2f}"
            text += f"<br>Agent Age: {int(row['age'])}"
            if 'completed_investments' in row and pd.notna(row['completed_investments']):
                text += f"<br>Completed Investments: {row['completed_investments']}"
        return text
    
    merged_df['hover_text'] = merged_df.apply(create_hover_text, axis=1)
    
    # --- 2. Build Plotly Figure ---
    fig = go.Figure()

    # Layer 1: Heatmap for current sugar (visuals only)
    fig.add_trace(go.Heatmap(
        z=sugar_map,
        colorscale='Greens',
        showscale=True,
        zmin=0, zmax=4, # Static color scale
        colorbar=dict(title="Current Sugar", x=1.15, xanchor="left"),
        hoverinfo='none'
    ))

    # Layer 2: Contour lines for max capacity
    fig.add_trace(go.Contour(
        z=static_sugar_map,
        showscale=False,
        contours_coloring='lines',
        line_width=1,
        line_color='gray',
        hoverinfo='none'
    ))

    # Layer 3: Agent markers
    # Define all categories so the legend is static
    if 'completed_investments' not in agent_df.columns:
        agent_df['completed_investments'] = '[]'
    
    agent_df['completed_list'] = agent_df['completed_investments'].apply(
        lambda x: json.loads(x) if isinstance(x, str) and x.startswith('[') else []
    )
    
    is_investing_mask = (agent_df['is_investing'] == 1)
    has_invested_mask = (agent_df['completed_list'].str.len() > 0)

    categories = [
        {"label": "Investing", "color": "blue", "symbol": "square", "size": 10, "mask": is_investing_mask},
        {"label": "Post-Investment", "color": "purple", "symbol": "diamond", "size": 12, "mask": ~is_investing_mask & has_invested_mask},
        {"label": "Foraging", "color": "red", "symbol": "circle", "size": 8, "mask": ~is_investing_mask & ~has_invested_mask},
    ]
    
    for cat in categories:
        subset = agent_df[cat["mask"]]
        # Always add the trace. If subset is empty, it draws nothing but keeps the legend entry.
        fig.add_trace(go.Scatter(
            x=subset['pos_y'], y=subset['pos_x'],
            mode='markers',
            marker=dict(color=cat['color'], symbol=cat['symbol'], size=cat['size'], line=dict(width=1, color='Black')),
            name=cat['label'],
            hoverinfo='none'
        ))

    # Layer 4: Transparent hover layer (must be last)
    fig.add_trace(go.Scatter(
        x=merged_df['x'],
        y=merged_df['y'],
        mode='markers',
        text=merged_df['hover_text'],
        hoverinfo='text',
        marker=dict(
            symbol='square',
            size=16,
            color='rgba(0,0,0,0)' # Invisible markers
        ),
        showlegend=False
    ))

    # --- 3. Configure Layout ---
    fig.update_layout(
        autosize=False,
        width=800, height=850, # Increased height for legend below
        xaxis=dict(showgrid=False, zeroline=False, ticks='', showticklabels=False, range=[-0.5, width - 0.5]),
        yaxis=dict(showgrid=False, zeroline=False, ticks='', showticklabels=False, range=[-0.5, height - 0.5], scaleanchor="x", scaleratio=1),
        legend=dict(
            title="Agent Status",
            orientation="h",
            yanchor="top",
            y=-0.05,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=40, r=40, b=40, t=40)
    )
    fig.update_yaxes(autorange="reversed")

    return fig

def main(args):
    db_mod_time = os.path.getmtime(DB_PATH) if DB_PATH.exists() else 0
    db_logger = DatabaseLogger(db_path=str(DB_PATH))

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

            sugar_map_json = st.session_state.run_params.get('sugar_map_distribution', '[]')
            st.session_state.static_sugar_map = np.array(json.loads(sugar_map_json))

            if not st.session_state.full_agent_df.empty:
                st.session_state.step = int(st.session_state.full_agent_df['step'].min())

    if 'full_agent_df' not in st.session_state or st.session_state.full_agent_df.empty:
        st.error(f"No agent data loaded for Run {run_id}.")
        return
        
    min_step = int(st.session_state.full_agent_df['step'].min())
    max_step = int(st.session_state.full_agent_df['step'].max())
    
    play_cols = st.sidebar.columns(2)
    if play_cols[0].button("Play", use_container_width=True):
        st.session_state.playing = True
    if play_cols[1].button("Stop", use_container_width=True):
        st.session_state.playing = False

    step_cols = st.sidebar.columns(2)
    if step_cols[0].button("Step Back", use_container_width=True):
        st.session_state.step = max(st.session_state.get('step', min_step) - 1, min_step)
        st.session_state.playing = False
    if step_cols[1].button("Step Forward", use_container_width=True):
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
    # Add .copy() to prevent SettingWithCopyWarning
    agent_df_step = st.session_state.full_agent_df.query(f"step == {current_step}").copy()
    sugar_map_step = st.session_state.all_sugar_maps.get(current_step)
    
    st.header(f"Spatial View for Run {run_id} at Step {current_step}")
    
    if sugar_map_step is not None:
        fig = render_spatial_view(db_logger, run_id, current_step, agent_df_step, sugar_map_step, st.session_state.run_params, st.session_state.static_sugar_map)
        st.plotly_chart(fig, use_container_width=False)
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