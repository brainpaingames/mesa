from pathlib import Path
import numpy as np
import mesa
from mesa.discrete_space import OrthogonalVonNeumannGrid
from mesa.discrete_space.property_layer import PropertyLayer
from agents import Trader
import subprocess
import datetime
from database_logger import DatabaseLogger

def Gini(model):
    """Helper to calculate the Gini coefficient for agent wealth."""
    agent_wealths = [agent.sugar for agent in model.agents_by_type[Trader]]
    if len(agent_wealths) < 2:
        return 0
    # Formula from https://en.wikipedia.org/wiki/Gini_coefficient
    x = np.sort(agent_wealths)
    n = len(x)
    cumx = np.cumsum(x, dtype=float)
    # The Gini coefficient is the area between the Lorenz curve and the line of equality
    return (n + 1 - 2 * np.sum(cumx) / cumx[-1]) / n

class SugarscapeG1mt(mesa.Model):
    """
    A manager class to run a Sugarscape where agents can invest.
    """
    def _get_git_info(self):
        """Helper function to get git hash and check for uncommitted changes."""
        try:
            git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip().decode('utf-8')
            git_status = subprocess.check_output(['git', 'status', '--porcelain']).strip().decode('utf-8')
            is_dirty = bool(git_status)
            return git_hash, is_dirty
        except (FileNotFoundError, subprocess.CalledProcessError):
            return "not a git repo", False

    def __init__(
        self,
        width=50,
        height=50,
        initial_population=200,
        agent_re_spawn=True,
        endowment_min=25,
        endowment_max=50,
        metabolism_min=1,
        metabolism_max=5,
        vision_min=1,
        vision_max=5,
        enable_investment=True,
        investment_cost=10,
        investment_duration=5,
        metabolism_reduction_factor=0.8,
        agent_look_ahead_horizon=15,
        run_group="default",
        description="A simulation run.",
        log_agent_data=False,
        dev_mode=False,
        seed=None,
    ):
        super().__init__(seed=seed)
        
        self.dev_mode = dev_mode
        self.db_logger = None

        if not self.dev_mode:
            git_hash, is_dirty = self._get_git_info()
            if is_dirty:
                raise RuntimeError(
                    "Git repository has uncommitted changes. "
                    "Please commit your changes before running a logged simulation."
                )
            
            run_meta = {
                "timestamp": datetime.datetime.now().isoformat(),
                "git_hash": git_hash,
                "run_group": run_group,
                "description": description,
            }
            
            model_params = {
                "width": width, "height": height,
                "initial_population": initial_population,
                "agent_re_spawn": int(agent_re_spawn),
                "endowment_min": endowment_min, "endowment_max": endowment_max,
                "metabolism_min": metabolism_min, "metabolism_max": metabolism_max,
                "vision_min": vision_min, "vision_max": vision_max,
                "enable_investment": int(enable_investment),
                "investment_cost": investment_cost,
                "investment_duration": investment_duration,
                "metabolism_reduction_factor": metabolism_reduction_factor,
                "agent_look_ahead_horizon": agent_look_ahead_horizon,
                "log_agent_data": int(log_agent_data),
            }
            
            self.db_logger = DatabaseLogger()
            self.run_id = self.db_logger.create_new_run(run_meta, model_params)

        self.width = width
        self.height = height
        self.initial_population = initial_population
        self.agent_re_spawn = agent_re_spawn
        self.endowment_min = endowment_min
        self.endowment_max = endowment_max
        self.metabolism_min = metabolism_min
        self.metabolism_max = metabolism_max
        self.vision_min = vision_min
        self.vision_max = vision_max

        self.enable_investment = enable_investment
        self.investment_cost = investment_cost
        self.investment_duration = investment_duration
        self.metabolism_reduction_factor = metabolism_reduction_factor
        self.agent_look_ahead_horizon = agent_look_ahead_horizon
        self.log_agent_data = log_agent_data

        self.running = True

        self.grid = OrthogonalVonNeumannGrid(
            (self.width, self.height), torus=False, random=self.random
        )
        
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "#Traders": lambda m: len(m.agents),
                "Total Sugar": lambda m: sum(a.sugar for a in m.agents),
                "Investing Agents": lambda m: len([a for a in m.agents if a.is_investing]),
                "Average Metabolism": lambda m: np.mean([a.metabolism_sugar for a in m.agents]) if m.agents else 0,
                "Gini": Gini,
                "Deaths": lambda m: getattr(m, 'deaths_this_step', 0),
            },
        )

        self.sugar_distribution = np.genfromtxt(Path(__file__).parent / "sugar-map.txt")
        self.grid.add_property_layer(
            PropertyLayer.from_data("sugar", self.sugar_distribution)
        )

        Trader.create_agents(
            self,
            self.initial_population,
            self.random.choices(self.grid.all_cells.cells, k=self.initial_population),
            sugar=self.rng.integers(
                self.endowment_min, self.endowment_max, (self.initial_population,), endpoint=True
            ),
            metabolism_sugar=self.rng.integers(
                self.metabolism_min, self.metabolism_max, (self.initial_population,), endpoint=True
            ),
            vision=self.rng.integers(
                self.vision_min, self.vision_max, (self.initial_population,), endpoint=True
            ),
        )

    def _add_new_agent(self):
        """Helper method to add a single new agent to the model."""
        
        empty_cells = [cell for cell in self.grid.all_cells.cells if cell.is_empty]
        if not empty_cells:
            return

        new_cell = self.random.choice(empty_cells)
        
        Trader.create_agents(
            self,
            1,
            [new_cell],
            sugar=self.rng.integers(
                self.endowment_min, self.endowment_max, endpoint=True
            ),
            metabolism_sugar=self.rng.integers(
                self.metabolism_min, self.metabolism_max, endpoint=True
            ),
            vision=self.rng.integers(
                self.vision_min, self.vision_max, endpoint=True
            ),
        )

    def step(self):
        """
        A unique step function that does staged activation.
        """
        self.grid.sugar.data = np.minimum(
            self.grid.sugar.data + 1, self.sugar_distribution
        )

        self.deaths_this_step = 0
        trader_shuffle = self.agents_by_type[Trader].shuffle()
        for agent in trader_shuffle:
            agent.step()
        
        if self.agent_re_spawn:
            current_population = len(self.agents)
            self.deaths_this_step = self.initial_population - current_population
            for _ in range(self.deaths_this_step):
                self._add_new_agent()

        self.datacollector.collect(self)
        
        if self.db_logger is not None:
            latest_data = {
                reporter: values[-1]
                for reporter, values in self.datacollector.model_vars.items()
            }
            self.db_logger.log_model_step(self.run_id, self.steps, latest_data)

            if self.log_agent_data:
                self.db_logger.log_agent_data(self.run_id, self.steps, self.schedule.agents)

    def run_model(self, step_count=1000):
        for _ in range(step_count):
            self.step()