# sugarscape_g1mt/utils.py

import numpy as np
import math
import json
from pathlib import Path

# --- Hard-Coded Economic Parameters for "Constant Payback" Model ---
INVESTMENT_PARAMS = {
    "benefit_growth_factor": 1.5,
    "constant_time_to_save": 20,
    "investment_duration": 5,
    "metabolism_during_investment": 3.0,
    "base_harvest_multiplier": 1.0,
    "max_sugar_capacity_for_ref_income": 4.0,
    "metabolism_normal_for_ref_income": 1.0
}

def get_harvest_multiplier(level: int, base_multiplier: float, growth_factor: float) -> float:
    """
    Calculates the harvest multiplier for a given investment level.
    This is a pure function.
    """
    return base_multiplier * (growth_factor ** level)


def Gini(model):
    """Helper to calculate the Gini coefficient for agent wealth."""
    from .agents import Trader # Moved here to prevent circular import
    agent_wealths = [agent.sugar for agent in model.agents_by_type[Trader]]
    if len(agent_wealths) < 2:
        return 0
    # Formula from https://en.wikipedia.org/wiki/Gini_coefficient
    x = np.sort(agent_wealths)
    n = len(x)
    cumx = np.cumsum(x, dtype=float)
    # The Gini coefficient is the area between the Lorenz curve and the line of equality
    return (n + 1 - 2 * np.sum(cumx) / cumx[-1]) / n

def get_distance(cell_1, cell_2):
    """
    Calculate the Euclidean distance between two positions.
    Used in Trader.move()
    """
    x1, y1 = cell_1.coordinate
    x2, y2 = cell_2.coordinate
    dx = x1 - x2
    dy = y1 - y2
    return math.sqrt(dx**2 + dy**2)

def load_config(path="sugarscape_g1mt/config.json"):
    """Loads the master JSON configuration file."""
    # This assumes the script is run from the parent directory of 'sugarscape_g1mt'
    # Adjust pathing if necessary, but this is robust for standard project execution.
    config_path = Path.cwd() / path
    with open(config_path, 'r') as f:
        return json.load(f)