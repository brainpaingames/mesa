import streamlit as st

st.set_page_config(
    page_title="Sugarscape Analysis Dashboard",
    layout="wide"
)

st.title("Sugarscape Analysis Dashboard")
st.markdown("""
Welcome to the analysis dashboard for the Sugarscape with Investment model.

Use the navigation sidebar on the left to select an analysis page:

- **Time Series Analysis:** Compare model-level reporters across multiple simulation runs.
- **Distribution Analysis:** Explore the distribution of agent attributes for selected runs over time.
- **Spatial Inspector:** View the 2D grid and agent locations for a single run at a specific time step.
""")