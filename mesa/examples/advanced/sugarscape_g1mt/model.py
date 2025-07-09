from pathlib import Path
import numpy as np
import mesa
from mesa.discrete_space import OrthogonalVonNeumannGrid
from mesa.discrete_space.property_layer import PropertyLayer
from .agents import Trader
import subprocess
import datetime
import json
from .database_logger import DatabaseLogger
from .investment import InvestmentOpportunity
from collections import defaultdict
from .contracts import Contract, ContractStatus

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
        sugar_regrowth_rate=1.0,
        investments_enabled=True,
        investment_portfolio_name="default",
        investment_json_path="sugarscape_g1mt/investments.json",
        endowment_min=25,
        endowment_max=50,
        metabolism_min=1,
        metabolism_max=5,
        vision_min=1,
        vision_max=5,
        agent_age_min=60,
        agent_age_max=100,
        agent_look_ahead_horizon=15,
        lender_vision=7,
        lender_look_ahead_horizon=20,
        run_group="default",
        description="A simulation run.",
        log_agent_data=False,
        dev_mode=False,
        seed=None,
        db_logger=None,
        run_id=None,
        tag="dev"
    ):
        super().__init__(seed=seed)

        self.dev_mode = dev_mode
        self.db_logger = db_logger
        self.run_id = run_id
        self.investment_portfolio_name = investment_portfolio_name
        self.investment_json_path = investment_json_path

        # This block is now only executed when running without a batch script
        if not self.dev_mode and self.db_logger is None:
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
                "tag": tag
            }

            model_params = {
                "width": width, "height": height,
                "initial_population": initial_population,
                "agent_re_spawn": int(agent_re_spawn),
                "sugar_regrowth_rate": sugar_regrowth_rate,
                "investments_enabled": int(investments_enabled),
                "investment_portfolio_name": investment_portfolio_name,
                "investment_json_path": investment_json_path,
                "endowment_min": endowment_min, "endowment_max": endowment_max,
                "metabolism_min": metabolism_min, "metabolism_max": metabolism_max,
                "vision_min": vision_min, "vision_max": vision_max,
                "agent_age_min": agent_age_min, "agent_age_max": agent_age_max,
                "agent_look_ahead_horizon": agent_look_ahead_horizon,
                "lender_vision": lender_vision,
                "lender_look_ahead_horizon": lender_look_ahead_horizon,
                "log_agent_data": int(log_agent_data),
            }

            self.db_logger = DatabaseLogger()
            self.run_id = self.db_logger.create_new_run(run_meta, model_params)

        self.width = width
        self.height = height
        self.initial_population = initial_population
        self.agent_re_spawn = agent_re_spawn
        self.sugar_regrowth_rate = sugar_regrowth_rate
        self.investments_enabled = investments_enabled
        self.endowment_min = endowment_min
        self.endowment_max = endowment_max
        self.metabolism_min = metabolism_min
        self.metabolism_max = metabolism_max
        self.vision_min = vision_min
        self.vision_max = vision_max
        self.agent_age_min = agent_age_min
        self.agent_age_max = agent_age_max
        self.agent_expected_lifespan = (agent_age_min + agent_age_max) / 2
        self.agent_look_ahead_horizon = agent_look_ahead_horizon
        self.log_agent_data = log_agent_data
        self.lender_vision = lender_vision
        self.lender_look_ahead_horizon = lender_look_ahead_horizon

        self.running = True

        self.grid = OrthogonalVonNeumannGrid(
            (self.width, self.height), torus=False, random=self.random
        )

        self.active_investment_portfolio = self._load_investment_portfolio()

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "#Traders": lambda m: len(m.agents),
                "Total Sugar": lambda m: sum(a.sugar for a in m.agents),
                "Investing Agents": lambda m: len([a for a in m.agents if a.is_investing]),
                "Average Metabolism": lambda m: np.mean([a.get_capability('metabolism_sugar') for a in m.agents]) if m.agents else 0,
                "Gini": Gini,
                "Deaths": lambda m: getattr(m, 'deaths_this_step', 0),
                "Active Loan Count": lambda m: sum(1 for c in m.contracts_by_id.values() if c.status == ContractStatus.ACTIVE),
                "Total Loan Principal": lambda m: sum(c.principal for c in m.contracts_by_id.values() if c.status == ContractStatus.ACTIVE),
            },
        )

        self.sugar_distribution = np.genfromtxt(Path(__file__).parent / "sugar-map.txt")
        self.grid.add_property_layer(
            PropertyLayer.from_data("sugar", self.sugar_distribution)
        )
        
        self.contracts_by_id = {}
        self.contracts_by_agent = defaultdict(set)
        self.next_contract_id = 0

        if self.db_logger and self.run_id is not None:
            self.db_logger.log_static_run_parameter(
                self.run_id,
                'sugar_map_distribution',
                json.dumps(self.sugar_distribution.tolist())
            )

        Trader.create_agents(
            self,
            self.initial_population,
            self.random.sample(self.grid.all_cells.cells, k=self.initial_population),
            sugar=self.rng.integers(
                self.endowment_min, self.endowment_max, (self.initial_population,), endpoint=True
            ),
            metabolism_sugar=self.rng.integers(
                self.metabolism_min, self.metabolism_max, (self.initial_population,), endpoint=True
            ),
            vision=self.rng.integers(
                self.vision_min, self.vision_max, (self.initial_population,), endpoint=True
            ),
            max_age=self.rng.integers(
                self.agent_age_min, self.agent_age_max, (self.initial_population,), endpoint=True
            ),
            expected_lifespan=self.agent_expected_lifespan,
            agent_look_ahead_horizon=self.agent_look_ahead_horizon,
            opportunities=self._create_agent_opportunities(),
            investments_enabled=self.investments_enabled,
            lender_vision=self.lender_vision,
            lender_look_ahead_horizon=self.lender_look_ahead_horizon
        )

    def register_contract(self, draft_contract: Contract) -> int:
        new_id = self.next_contract_id
        draft_contract.status = ContractStatus.ACTIVE
        self.contracts_by_id[new_id] = draft_contract
        self.contracts_by_agent[draft_contract.creditor_id].add(new_id)
        self.contracts_by_agent[draft_contract.debtor_id].add(new_id)
        self.next_contract_id += 1
        return new_id

    def _load_investment_portfolio(self):
        """Loads and builds the active investment portfolio from a JSON file."""
        try:
            with open(self.investment_json_path, 'r') as f:
                all_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: Investment JSON file not found at {self.investment_json_path}")
            return []
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {self.investment_json_path}")
            return []

        definitions = all_data.get("definitions", {})
        portfolios = all_data.get("portfolios", {})

        portfolio_keys = portfolios.get(self.investment_portfolio_name)
        if portfolio_keys is None:
            print(f"Warning: Portfolio '{self.investment_portfolio_name}' not found in {self.investment_json_path}. No investments will be loaded.")
            return []

        portfolio = []
        for key in portfolio_keys:
            if key in definitions:
                portfolio.append(InvestmentOpportunity(definitions[key], model_context=self))
            else:
                print(f"Warning: Investment key '{key}' from portfolio '{self.investment_portfolio_name}' not found in definitions.")

        return portfolio

    def _create_agent_opportunities(self):
        """Creates a fresh list of investment opportunities for an agent."""
        return self.active_investment_portfolio.copy()

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
            max_age=self.rng.integers(
                self.agent_age_min, self.agent_age_max, endpoint=True
            ),
            expected_lifespan=self.agent_expected_lifespan,
            agent_look_ahead_horizon=self.agent_look_ahead_horizon,
            opportunities=self._create_agent_opportunities(),
            investments_enabled=self.investments_enabled,
            lender_vision=self.lender_vision,
            lender_look_ahead_horizon=self.lender_look_ahead_horizon
        )

    def step(self):
        """
        A unique step function that does staged activation.
        """
        self.grid.sugar.data = np.minimum(
            self.grid.sugar.data + self.sugar_regrowth_rate, self.sugar_distribution
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
                self.db_logger.log_agent_data(self.run_id, self.steps, self.agents)
                self.db_logger.log_spatial_layer(self.run_id, self.steps, "sugar", self.grid.sugar.data)

    def run_model(self, step_count=1000):
        for _ in range(step_count):
            self.step()