import sys
from .model import SugarscapeG1mt
from mesa.visualization import Slider, SolaraViz, make_plot_component
from mesa.visualization.components import AgentPortrayalStyle, PropertyLayerStyle
from mesa.visualization.components.matplotlib_components import make_mpl_space_component

# Check for our custom flag after the '--' separator.
IS_DEV_MODE = "--mesa-dev" in sys.argv

def agent_portrayal(agent):
    """
    Defines how to draw the agents on the grid.
    """
    if agent.is_investing:
        return AgentPortrayalStyle(
            x=agent.cell.coordinate[0],
            y=agent.cell.coordinate[1],
            color="blue",
            marker="s",
            size=20,
            zorder=2,
        )
    return AgentPortrayalStyle(
        x=agent.cell.coordinate[0],
        y=agent.cell.coordinate[1],
        color="red",
        marker="o",
        size=10,
        zorder=1,
    )


def propertylayer_portrayal(layer):
    """
    Defines how to draw the property layer (sugar) on the grid.
    """
    return PropertyLayerStyle(
        color="green",
        alpha=0.8,
        colorbar=True,
        vmin=0,
        vmax=10
    )


sugarscape_space = make_mpl_space_component(
    agent_portrayal=agent_portrayal,
    propertylayer_portrayal=propertylayer_portrayal,
)

model_params = {
    "seed": {
        "type": "InputText",
        "value": 42,
        "label": "Random Seed",
    },
    "width": 50,
    "height": 50,
    "run_group": {"type": "InputText", "value": "dev_run", "label": "Run Group/Experiment Name"},
    "description": {"type": "InputText", "value": "A developer run.", "label": "Run Description"},
    "log_agent_data": {"type": "Checkbox", "value": False, "label": "Log Agent-Level Data (creates large DB)"},
    "initial_population": Slider(
        "Initial Population", value=400, min=0, max=600, step=50
    ),
    "agent_re_spawn": {"type": "Checkbox", "value": True, "label": "Re-spawn Dead Agents"},
    "investments_enabled": {"type": "Checkbox", "value": True, "label": "Enable Investments"},
    "investment_portfolio_name": {"type": "InputText", "value": "default", "label": "Investment Portfolio Name"},
    "investment_json_path": {"type": "InputText", "value": "sugarscape_g1mt/investments.json", "label": "Investment JSON Path"},
    "sugar_regrowth_rate": Slider("Sugar Regrowth Rate (>4 is instant)", value=1.0, min=0.0, max=5.0, step=0.1),
    "endowment_min": Slider("Min Initial Endowment", value=15, min=0, max=30, step=1),
    "endowment_max": Slider("Max Initial Endowment", value=15, min=0, max=30, step=1),
    "metabolism_min": Slider("Min Metabolism", value=1.0, min=0.0, max=5.0, step=0.1),
    "metabolism_max": Slider("Max Metabolism", value=4.0, min=0.0, max=5.0, step=0.1),
    "vision_min": Slider("Min Vision", value=1, min=0, max=10, step=1),
    "vision_max": Slider("Max Vision", value=6, min=0, max=10, step=1),
    "agent_age_min": Slider("Min Agent Age", value=60, min=0, max=150, step=5),
    "agent_age_max": Slider("Max Agent Age", value=60, min=0, max=150, step=5),
    "agent_look_ahead_horizon": Slider("Agent Planning Horizon", value=15, min=5, max=50, step=1),
}

if IS_DEV_MODE:
    model_params["dev_mode"] = True

model = SugarscapeG1mt(dev_mode=IS_DEV_MODE)

page_name = "Sugarscape with Investment"
if IS_DEV_MODE:
    page_name = "DEV MODE - " + page_name

page = SolaraViz(
    model,
    components=[
        sugarscape_space,
        make_plot_component("#Traders"),
        make_plot_component("Total Sugar"),
        make_plot_component("Investing Agents"),
        make_plot_component("Average Metabolism"),
        make_plot_component("Gini"), 
        make_plot_component("Deaths"), 
    ],
    model_params=model_params,
    name=page_name,
    play_interval=150,
)
page