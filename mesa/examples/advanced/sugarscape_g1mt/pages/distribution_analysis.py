import streamlit as st
import plotly.express as px
import os
import argparse
from sugarscape_g1mt import analysis_helpers as h

st.set_page_config(layout="wide", page_title="Distribution Analysis")
st.title("Distribution Analysis")
st.markdown("Explore the distribution of agent attributes for a single simulation run over time.")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Number of recent runs to show. 0 for all.")
    parser.add_argument("--include-tests", action="store_true", help="Include test runs.")
    try:
        # When run via streamlit, it might have extra args we need to ignore
        args, _ = parser.parse_known_args()
        return args
    except SystemExit:
        return parser.parse_args([])

def main(args):
    db_mod_time = os.path.getmtime(h.DB_PATH) if h.DB_PATH.exists() else 0

    st.sidebar.header("Controls")
    
    agent_data_runs = h.get_runs_with_agent_data(args.limit, args.include_tests, db_mod_time)

    if agent_data_runs.empty:
        st.warning("No runs with agent-level data logging found. Please run a simulation with 'Log Agent-Level Data' enabled.")
        return

    selected_display_run = st.sidebar.selectbox(
        "Select a run to analyze:",
        options=agent_data_runs['display'].tolist(),
        index=0
    )

    if not selected_display_run:
        return
        
    selected_id = agent_data_runs[agent_data_runs['display'] == selected_display_run]['run_id'].iloc[0]
    
    agent_data = h.get_agent_data_for_run(selected_id, db_mod_time)

    if agent_data.empty:
        st.warning(f"No agent data found for run {selected_id}.")
        return

    max_step = agent_data['step'].max()
    selected_step = st.sidebar.slider("Select Simulation Step", 0, int(max_step), int(max_step))
    
    step_data = agent_data[agent_data['step'] == selected_step]

    if step_data.empty:
        st.warning(f"No agent data available at step {selected_step}.")
        return

    st.markdown(f"### Distributions at Step `{selected_step}` for Run `{selected_id}`")
    
    exclude_cols = ['run_id', 'step', 'agent_id']
    available_attributes = [col for col in agent_data.columns if col not in exclude_cols]
    
    default_attrs = [a for a in ['sugar', 'age'] if a in available_attributes]
    if not default_attrs and available_attributes:
        default_attrs = [available_attributes[0]]

    selected_attributes = st.multiselect(
        "Select attributes to visualize:",
        options=available_attributes,
        default=default_attrs
    )

    if not selected_attributes:
        st.info("Select one or more attributes to see their distributions.")
        return

    for attribute in selected_attributes:
        fig = px.histogram(
            step_data, 
            x=attribute, 
            title=f"Distribution of Agent {attribute.replace('_', ' ').capitalize()} at Step {selected_step}",
            nbins=30,
        )
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    cli_args = parse_args()
    main(cli_args)