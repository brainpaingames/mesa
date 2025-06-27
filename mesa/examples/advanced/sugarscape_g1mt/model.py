from pathlib import Path

import numpy as np

import mesa
from mesa.discrete_space import OrthogonalVonNeumannGrid
from mesa.discrete_space.property_layer import PropertyLayer
# The agent class is imported directly, not relatively
from agents import Trader


class SugarscapeG1mt(mesa.Model):
    """
    A simplified manager class to run a Sugarscape with sugar-only Traders.
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
        seed=None,
    ):
        super().__init__(seed=seed)
        # Initiate width and height of sugarscape
        self.width = width
        self.height = height

        # Initiate population attributes
        self.running = True

        # Initiate mesa grid class
        self.grid = OrthogonalVonNeumannGrid(
            (self.width, self.height), torus=False, random=self.random
        )
        # Initiate datacollector
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "#Traders": lambda m: len(m.agents),
                "Total Sugar": lambda m: sum(a.sugar for a in m.agents),
            },
        )

        # Read in landscape file from supplementary material
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
            agent.move()
            agent.eat()
            agent.maybe_die()

        # Collect model level data
        self.datacollector.collect(self)

    def run_model(self, step_count=1000):
        for _ in range(step_count):
            self.step()