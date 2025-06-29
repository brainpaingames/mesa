from pathlib import Path

import numpy as np

import mesa
from mesa.discrete_space import OrthogonalVonNeumannGrid
from mesa.discrete_space.property_layer import PropertyLayer
from agents import Trader


class SugarscapeG1mt(mesa.Model):
    """
    A manager class to run a Sugarscape where agents can invest.
    """

    def __init__(
        self,
        width=50,
        height=50,
        initial_population=200,
        endowment_min=25,
        endowment_max=50,
        metabolism_min=1,
        metabolism_max=5,
        vision_min=1,
        vision_max=5,
        # --- START of Functional Additions ---
        enable_investment=True,
        investment_cost=10,
        investment_duration=5,
        metabolism_reduction_factor=0.8,
        agent_look_ahead_horizon=15,
        # --- END of Functional Additions ---
        seed=None,
    ):
        super().__init__(seed=seed)
        # Initiate width and height of sugarscape
        self.width = width
        self.height = height

        # --- START of Functional Additions ---
        # Store model parameters
        self.enable_investment = enable_investment
        self.investment_cost = investment_cost
        self.investment_duration = investment_duration
        self.metabolism_reduction_factor = metabolism_reduction_factor
        self.agent_look_ahead_horizon = agent_look_ahead_horizon
        # --- END of Functional Additions ---

        # Initiate population attributes
        self.running = True

        # Initiate mesa grid class
        self.grid = OrthogonalVonNeumannGrid(
            (self.width, self.height), torus=False, random=self.random
        )
        
        # Updated DataCollector for new metrics
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "#Traders": lambda m: len(m.agents),
                "Total Sugar": lambda m: sum(a.sugar for a in m.agents),
                "Investing Agents": lambda m: len([a for a in m.agents if a.is_investing]),
                "Average Metabolism": lambda m: np.mean([a.metabolism_sugar for a in m.agents]) if m.agents else 0,
            },
        )

        self.sugar_distribution = np.genfromtxt(Path(__file__).parent / "sugar-map.txt")
        self.grid.add_property_layer(
            PropertyLayer.from_data("sugar", self.sugar_distribution)
        )

        # Create agents
        Trader.create_agents(
            self,
            initial_population,
            self.random.choices(self.grid.all_cells.cells, k=initial_population),
            sugar=self.rng.integers(
                endowment_min, endowment_max, (initial_population,), endpoint=True
            ),
            metabolism_sugar=self.rng.integers(
                metabolism_min, metabolism_max, (initial_population,), endpoint=True
            ),
            vision=self.rng.integers(
                vision_min, vision_max, (initial_population,), endpoint=True
            ),
        )

    def step(self):
        """
        A unique step function that does staged activation.
        First, the sugar grows back, then agents act.
        """
        # Grow sugar
        self.grid.sugar.data = np.minimum(
            self.grid.sugar.data + 1, self.sugar_distribution
        )

        # Step trader agents
        # To account for agent death and removal, we need a separate data structure to
        # iterate over.
        trader_shuffle = self.agents_by_type[Trader].shuffle()
        for agent in trader_shuffle:
            agent.step()

        # Collect model level data
        self.datacollector.collect(self)

    def run_model(self, step_count=1000):
        for _ in range(step_count):
            self.step()