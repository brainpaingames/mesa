import math

from mesa.discrete_space import CellAgent


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


class Trader(CellAgent):
    """
    A trader agent that can choose between foraging and investing.
    - Has a metabolism of sugar.
    - Harvests sugar to survive.
    - Can invest sugar to permanently reduce metabolism.
    """

    def __init__(self, model, cell, sugar=0, metabolism_sugar=0, vision=0, max_age=0, expected_lifespan=0, agent_look_ahead_horizon=15, opportunities=None):
        super().__init__(model)
        self.cell = cell
        self.sugar = sugar
        self.max_age = max_age
        self.expected_lifespan = expected_lifespan
        self.age = 0

        self.capabilities = {
            "vision": vision,
            "metabolism_sugar": metabolism_sugar,
            "harvest_multipliers": [0.0, 1.0, 1.0, 1.0, 1.0],
            "agent_look_ahead_horizon": agent_look_ahead_horizon
        }
        self.available_opportunities = opportunities if opportunities is not None else []
        self.completed_investment_names = set()
        self.is_investing = False
        self.investment_counter = 0
        self.current_investment = None

    def get_reportable_attributes(self):
        """Returns a dictionary of agent attributes for database logging."""
        pos_x, pos_y = (self.cell.coordinate[0], self.cell.coordinate[1]) if self.cell is not None else (None, None)
        return {
            "pos_x": pos_x,
            "pos_y": pos_y,
            "sugar": float(self.sugar),
            "metabolism": float(self.capabilities["metabolism_sugar"]),
            "vision": int(self.capabilities["vision"]),
            "age": int(self.age),
            "max_age": int(self.max_age),
            "expected_lifespan": float(self.expected_lifespan),
            "is_investing": int(self.is_investing),
            "agent_look_ahead_horizon": int(self.capabilities["agent_look_ahead_horizon"]),
        }

    def calculate_welfare(self, sugar):
        """
        Helper function for self.move().
        In this simplified model, welfare is simply the amount of sugar.
        """
        return sugar

    def is_starved(self):
        """
        Helper function for self.maybe_die().
        """
        return self.sugar <= 0

    def get_potential_harvest(self, cell):
        """Calculates the potential sugar harvest from a given cell based on current capabilities."""
        multipliers = self.capabilities["harvest_multipliers"]
        capacity = int(self.model.sugar_distribution[cell.coordinate[1], cell.coordinate[0]])
        return cell.sugar * multipliers[capacity]

    def find_best_foraging_cell(self):
        """Finds the best cell to forage from in the agent's vision, including its current cell."""
        vision = self.capabilities['vision']

        neighboring_cells = [
            cell
            for cell in self.cell.get_neighborhood(vision, include_center=True)
            if cell.is_empty or cell == self.cell
        ]
        
        if not neighboring_cells:
            return None

        welfares = [
            self.calculate_welfare(self.sugar + self.get_potential_harvest(cell))
            for cell in neighboring_cells
        ]

        max_welfare = max(welfares)
        candidate_indices = [
            i for i, w in enumerate(welfares) if math.isclose(w, max_welfare)
        ]
        candidates = [neighboring_cells[i] for i in candidate_indices]

        min_dist = min(get_distance(self.cell, cell) for cell in candidates)

        final_candidates = [
            cell
            for cell in candidates
            if math.isclose(get_distance(self.cell, cell), min_dist, rel_tol=1e-2)
        ]

        return self.random.choice(final_candidates)

    def get_max_potential_harvest(self):
        """Helper to perceive the best foraging spot in the current vision for forecasting."""
        best_cell = self.find_best_foraging_cell()
        return self.get_potential_harvest(best_cell) if best_cell else 0

    def simulate_forage_scenario(self, horizon):
        """Simulates future sugar if agent only forages."""
        sim_sugar = self.sugar
        expected_harvest = self.get_max_potential_harvest()
        metabolism = self.capabilities["metabolism_sugar"]

        for _ in range(horizon):
            sim_sugar += expected_harvest
            sim_sugar -= metabolism
            if sim_sugar <= 0:
                return -1, True
        return sim_sugar, False

    def step(self):
        """Main step logic for the agent."""
        if self.is_investing:
            self.investment_counter -= 1
            if self.investment_counter <= 0:
                self.current_investment.apply_reward_to(self.capabilities)
                self.completed_investment_names.add(self.current_investment.name)
                self.is_investing = False
                self.current_investment = None
        else:
            # --- Agent Decision Logic ---
            horizon = self.capabilities['agent_look_ahead_horizon']

            # 1. Evaluate the status quo (foraging)
            forage_utility, forage_death = self.simulate_forage_scenario(horizon)
            
            best_utility = forage_utility
            best_is_death = forage_death
            chosen_action = ("FORAGE", None)

            # 2. Evaluate all available investment opportunities
            for opp in self.available_opportunities:
                if opp.is_available(self):
                    invest_utility, invest_death = opp.calculate_utility(self, horizon)
                    
                    # Prioritize survival, then highest utility
                    if best_is_death and not invest_death:
                        best_utility = invest_utility
                        best_is_death = invest_death
                        chosen_action = ("INVEST", opp)
                    elif not best_is_death and not invest_death:
                        if invest_utility > best_utility:
                            best_utility = invest_utility
                            chosen_action = ("INVEST", opp)

            # 3. Execute the chosen action
            action_type, investment_opp = chosen_action
            if action_type == "INVEST":
                self.is_investing = True
                self.current_investment = investment_opp
                self.investment_counter = investment_opp.cost["duration"]
                self.capabilities["metabolism_sugar"] = investment_opp.cost["metabolism_during_investment"]
                self.available_opportunities.remove(investment_opp)
            else: # FORAGE
                self.move()
                self.eat()

        self.age += 1
        self.metabolize()
        self.maybe_die()

    def move(self):
        """Moves the agent to the best foraging cell in its vision."""
        best_cell = self.find_best_foraging_cell()
        if best_cell:
            self.cell = best_cell

    def eat(self):
        """
        Agent harvests sugar from its current cell.
        """
        self.sugar += self.get_potential_harvest(self.cell)
        self.cell.sugar = 0

    def metabolize(self):
        """Agent consumes sugar for metabolism."""
        self.sugar -= self.capabilities['metabolism_sugar']
        
    def maybe_die(self):
        """
        Function to remove agents who have consumed all their sugar.
        """
        if self.is_starved() or self.age >= self.max_age:
            self.remove()