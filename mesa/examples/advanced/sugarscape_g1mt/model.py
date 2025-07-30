# sugarscape_g1mt/model.py

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
from .contracts import Contract, ContractStatus, ContractType
from dataclasses import asdict
from .utils import Gini, load_config


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

    def __init__(self, **kwargs):
        # --- 1. Load config, merge with kwargs to get final parameters ---
        config = load_config()
        defaults = {}
        for section in config.values():
            defaults.update(section)
        # Passed-in kwargs override the defaults from the config file
        params = {**defaults, **kwargs}

        # --- 2. Initialize Mesa Model with seed ---
        seed = params.get('seed')
        super().__init__(seed=seed)

        # --- 3. Set special attributes and cache ---
        self._agents_by_id_cache = None
        self.dev_mode = params.get('dev_mode', False)
        self.db_logger = params.get('db_logger')
        self.run_id = params.get('run_id')


        # --- 5. Set all parameters as model attributes ---
        for key, value in params.items():
            setattr(self, key, value)
        
        # --- 6. Set up DB Logger if not provided (i.e., when not running from a batch) ---
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
                "run_group": self.run_group,
                "description": self.description,
                "tag": self.tag
            }

            # Log all parameters except the DB objects themselves
            db_params_to_log = {k: v for k, v in params.items() if k not in ['db_logger', 'run_id']}
            
            self.db_logger = DatabaseLogger()
            self.run_id = self.db_logger.create_new_run(run_meta, db_params_to_log)

        # --- 7. Initialize model components ---
        self.agent_expected_lifespan = (self.agent_age_min + self.agent_age_max) / 2
        self.running = True
        
        self.grid = OrthogonalVonNeumannGrid(
            (self.width, self.height), torus=False, random=self.random
        )

        self.active_investment_portfolio = self._load_investment_portfolio()

        # Helper to get a list of new loan contracts for reporters
        def get_new_contracts_by_type(model, contract_type):
            return [model.contracts_by_id[cid] for cid in model.new_contracts_this_step 
                    if model.contracts_by_id[cid].contract_type == contract_type]

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "#Traders": lambda m: len(m.agents),
                "Total Sugar": lambda m: sum(a.sugar for a in m.agents),
                "Investing Agents": lambda m: len([a for a in m.agents if a.is_investing]),
                "Average Metabolism": lambda m: np.mean([a.get_capability('metabolism_sugar') for a in m.agents]) if m.agents else 0,
                "Gini": Gini,
                "Deaths": lambda m: getattr(m, 'deaths_this_step', 0),
                "Active Loan Count": lambda m: sum(1 for c in m.contracts_by_id.values() if c.status == ContractStatus.ACTIVE and c.contract_type == ContractType.TERM_LOAN),
                "Total Loan Principal": lambda m: sum(c.principal for c in m.contracts_by_id.values() if c.status == ContractStatus.ACTIVE and c.contract_type == ContractType.TERM_LOAN),
                "Active Deposit Count": lambda m: sum(1 for c in m.contracts_by_id.values() if c.status == ContractStatus.ACTIVE and c.contract_type == ContractType.DEMAND_DEPOSIT),
                "Total Deposit Principal": lambda m: sum(c.current_principal for c in m.contracts_by_id.values() if c.status == ContractStatus.ACTIVE and c.contract_type == ContractType.DEMAND_DEPOSIT),
                "Avg Loan Rate (Per-Step)": lambda m: 
                    np.mean([c.per_step_rate for c in get_new_contracts_by_type(m, ContractType.TERM_LOAN)]) 
                    if len(get_new_contracts_by_type(m, ContractType.TERM_LOAN)) > 0 else 0,
                "Avg Deposit Rate (Per-Step)": lambda m:
                    np.mean([c.per_step_rate for c in get_new_contracts_by_type(m, ContractType.DEMAND_DEPOSIT)])
                    if len(get_new_contracts_by_type(m, ContractType.DEMAND_DEPOSIT)) > 0 else 0,
                "Ledger": lambda m: m.get_ledger_snapshot(),
            },
        )

        self.sugar_distribution = np.genfromtxt(Path(__file__).parent / "sugar-map.txt")
        self.grid.add_property_layer(
            PropertyLayer.from_data("sugar", self.sugar_distribution)
        )
        
        self.contracts_by_id = {}
        self.contracts_by_agent = defaultdict(set)
        self.next_contract_id = 0
        self.new_contracts_this_step = []

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
            lending_enabled=self.lending_enabled,
            deposits_enabled=self.deposits_enabled,
            deposit_buffer_horizon=self.deposit_buffer_horizon,
            lender_vision=self.lender_vision,
            lender_look_ahead_horizon=self.lender_look_ahead_horizon,
            spoilage_rate=self.agent_spoilage_rate
        )
    
    # --- LAZY-LOADED CACHE GETTER ---
    def get_agent_by_id(self, agent_id):
        """
        Efficiently finds an agent by its ID using a lazily-loaded,
        step-specific cache.
        """
        if self._agents_by_id_cache is None:
            self._agents_by_id_cache = {agent.unique_id: agent for agent in self.agents}
        return self._agents_by_id_cache.get(agent_id)

    def register_contract(self, draft_contract: Contract) -> int:
        new_id = self.next_contract_id
        draft_contract.status = ContractStatus.ACTIVE
        self.contracts_by_id[new_id] = draft_contract
        self.contracts_by_agent[draft_contract.creditor_id].add(new_id)
        self.contracts_by_agent[draft_contract.debtor_id].add(new_id)
        self.new_contracts_this_step.append(new_id) # Track for this step's reporters
        self.next_contract_id += 1
        return new_id

    def update_contract_status(self, contract_id: int, new_status: ContractStatus):
        """Safely updates a contract's status and cleans the index if it becomes inactive."""
        if contract_id in self.contracts_by_id:
            contract = self.contracts_by_id[contract_id]
            contract.status = new_status

            if new_status in [ContractStatus.REPAID, ContractStatus.DEFAULTED, ContractStatus.CLOSED]:
                self.contracts_by_agent[contract.creditor_id].discard(contract_id)
                self.contracts_by_agent[contract.debtor_id].discard(contract_id)

    def process_deposit_call(self, contract_id: int, contract_to_call: Contract, amount_to_call: float):
        """
        Authoritative function to process a (potentially fractional) deposit withdrawal.
        """
        creditor = self.get_agent_by_id(contract_to_call.creditor_id)
        debtor = self.get_agent_by_id(contract_to_call.debtor_id)

        # Ensure both parties are still in the simulation
        if not creditor or not debtor:
            return

        # Sanity checks
        if amount_to_call <= 0:
            return
        if amount_to_call > contract_to_call.current_principal:
            amount_to_call = contract_to_call.current_principal # Failsafe

        payment = min(amount_to_call, debtor.sugar)
        
        debtor.sugar -= payment
        creditor.sugar += payment
        contract_to_call.current_principal -= payment

        if payment < amount_to_call:
            # Debtor defaulted on the call, but we record the partial payment.
            # A future bankruptcy epic would handle the remaining claim.
            pass

        if contract_to_call.current_principal <= 0:
            self.update_contract_status(contract_id, ContractStatus.CLOSED)

    def get_ledger_snapshot(self) -> str:
        """Serializes the current state of the contract book to a JSON string."""
        serializable_ledger = {}
        for contract_id, contract_obj in self.contracts_by_id.items():
            contract_dict = asdict(contract_obj)
            # Convert enums to strings for JSON compatibility
            contract_dict['contract_type'] = contract_dict['contract_type'].name
            contract_dict['status'] = contract_dict['status'].name
            serializable_ledger[contract_id] = contract_dict
        return json.dumps(serializable_ledger, indent=2)

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
            lending_enabled=self.lending_enabled,
            deposits_enabled=self.deposits_enabled,
            deposit_buffer_horizon=self.deposit_buffer_horizon,
            lender_vision=self.lender_vision,
            lender_look_ahead_horizon=self.lender_look_ahead_horizon,
            spoilage_rate=self.agent_spoilage_rate
        )

    def step(self):
        """
        A unique step function that does staged activation.
        """
        self._agents_by_id_cache = None
        self.new_contracts_this_step.clear()

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