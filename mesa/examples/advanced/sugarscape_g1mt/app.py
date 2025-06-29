# The model class is imported directly, not relatively
from model import SugarscapeG1mt
from mesa.visualization import Slider, SolaraViz, make_plot_component
# We MUST import PropertyLayerStyle because we are going to use it.
from mesa.visualization.components import AgentPortrayalStyle, PropertyLayerStyle
from mesa.visualization.components.matplotlib_components import make_mpl_space_component


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
    This function must return a PropertyLayerStyle object. The visualization
    engine will use the single 'color' provided and vary its intensity.
    """
    # We will use "green" for the sugar layer. This is a valid single color.
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
    # Population parameters
    "initial_population": Slider(
        "Initial Population", value=200, min=50, max=500, step=10
    ),
    # Agent endowment parameters
    "endowment_min": Slider("Min Initial Endowment", value=25, min=5, max=30, step=1),
    "endowment_max": Slider("Max Initial Endowment", value=50, min=30, max=100, step=1),
    # Metabolism parameters
    "metabolism_min": Slider("Min Metabolism", value=1, min=1, max=3, step=1),
    "metabolism_max": Slider("Max Metabolism", value=5, min=3, max=8, step=1),
    # Vision parameters
    "vision_min": Slider("Min Vision", value=1, min=1, max=3, step=1),
    "vision_max": Slider("Max Vision", value=5, min=3, max=8, step=1),
    # --- START of Functional Additions ---
    # Investment parameters
    "enable_investment": {"type": "Checkbox", "value": True, "label": "Enable Investment"},
    "investment_cost": Slider("Investment Cost", value=10, min=0, max=50, step=1),
    "investment_duration": Slider("Investment Duration", value=5, min=1, max=20, step=1),
    "metabolism_reduction_factor": Slider("Metabolism Reduction Factor", value=0.8, min=0.1, max=1.0, step=0.05),
    "agent_look_ahead_horizon": Slider("Agent Planning Horizon", value=15, min=5, max=50, step=1),
    # --- END of Functional Additions ---
}

# The model class is imported from model.py
model = SugarscapeG1mt()

# The visualization page
page = SolaraViz(
    model,
    components=[
        sugarscape_space,
        make_plot_component("#Traders"),
        make_plot_component("Total Sugar"),
        make_plot_component("Investing Agents"),
        make_plot_component("Average Metabolism"),
    ],
    model_params=model_params,
    name="Sugarscape with Investment",
    play_interval=150,
)
page  # noqa