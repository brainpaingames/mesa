# sugarscape_g1mt/utils.py

import numpy as np
import math
import json
from pathlib import Path



def get_harvest_multiplier(level: int, base_multiplier: float, growth_factor: float) -> float:
    """
    Calculates the harvest multiplier for a given investment level.
    This is a pure function.
    """
    return base_multiplier * (growth_factor ** level)


def get_metabolism_during_investment(current_level: int, duration: int, constant_k: int, base_multiplier: float, growth_factor: float, reference_sugar: float, reference_metabolism: float) -> float:
    """
    Calculates the required metabolism during an investment to ensure a "Constant Time to Save".
    This is a pure function derived from the economic model's core requirements.
    """
    current_multiplier = get_harvest_multiplier(current_level, base_multiplier, growth_factor)
    
    ref_gross_income = current_multiplier * reference_sugar
    ref_net_savings = max(0, ref_gross_income - reference_metabolism)
    
    # Formula derived from the design requirements
    return (constant_k * ref_net_savings) / (duration + 1)


def get_capital_requirement(metabolism_during_investment: float, duration: int) -> float:
    """
    Calculates the total capital an agent must possess to survive the investment period.
    This is a pure function.
    """
    # The agent must survive the investment period plus the step it completes.
    return metabolism_during_investment * (duration + 1)


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