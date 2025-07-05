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

    def __init__(self, model, cell, sugar=0, metabolism_sugar=0, vision=0, max_age=0, expected_lifespan=0, opportunities=None):
        super().__init__(model)
        self.cell = cell
        self.sugar = sugar
        self.max_age = max_age
        self.expected_lifespan = expected_lifespan
        self.age = 0

        self.capabilities = {
            "vision": vision,
            "metabolism_sugar": metabolism_sugar,
            "harvest_multipliers": [0.0, 1.0, 1.0, 1.0, 1.0]
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
            # Placeholder for Phase 4: For now, just forage.
            self.move()
            self.eat()

        self.age += 1
        self.metabolize()
        self.maybe_die()

    def move(self):
        """
        Function for the trader agent to find the best cell to move to.
        1. Identify all possible neighboring cells within its vision.
        2. Determine which move maximizes sugar intake (welfare).
        3. Find the closest of the best options.
        4. Move to the chosen cell.
        """
        vision = self.capabilities['vision']
        multipliers = self.capabilities['harvest_multipliers']

        neighboring_cells = [
            cell
            for cell in self.cell.get_neighborhood(vision, include_center=True)
            if cell.is_empty
        ]

        welfares = [
            self.calculate_welfare(self.sugar + (cell.sugar * multipliers[int(self.model.sugar_distribution[cell.coordinate[1], cell.coordinate[0]])]))
            for cell in neighboring_cells
        ]

        if not welfares:
            return

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

        self.cell = self.random.choice(final_candidates)

    def eat(self):
        """
        Agent harvests sugar from its current cell.
        """
        capacity = int(self.model.sugar_distribution[self.cell.coordinate[1], self.cell.coordinate[0]])
        multiplier = self.capabilities['harvest_multipliers'][capacity]
        self.sugar += self.cell.sugar * multiplier
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