import math

from mesa.discrete_space import CellAgent


# Helper function
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
    A trader agent that only focuses on sugar.
    - Has a metabolism of sugar.
    - Harvests sugar to survive.
    """
    # --- START of Functional Additions for Milestone 2 ---
    INVESTMENT_DURATION = 3
    INVESTMENT_COST = 1
    METABOLISM_REDUCTION_FACTOR = 0.3
    LOOK_AHEAD_HORIZON = 15
    # --- END of Functional Additions for Milestone 2 ---

    def __init__(self, model, cell, sugar=0, metabolism_sugar=0, vision=0):
        super().__init__(model)
        self.cell = cell
        self.sugar = sugar
        self.metabolism_sugar = metabolism_sugar
        self.vision = vision
        # --- START of Functional Additions for Milestone 2 ---
        self.is_investing = False
        self.investment_counter = 0
        # --- END of Functional Additions for Milestone 2 ---

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

    # --- START of Functional Additions for Milestone 2 ---
    def get_max_harvestable_sugar(self):
        """Helper to perceive the best foraging spot in the current vision."""
        empty_cells = [
            cell
            for cell in self.cell.get_neighborhood(self.vision, include_center=False)
            if cell.is_empty
        ]
        if not empty_cells:
            return 0
        return max(cell.sugar for cell in empty_cells)

    def simulate_forage_scenario(self, horizon):
        """Simulates future sugar if agent only forages."""
        sim_sugar = self.sugar
        expected_harvest = self.get_max_harvestable_sugar()
        for _ in range(horizon):
            sim_sugar += expected_harvest
            sim_sugar -= self.metabolism_sugar
            if sim_sugar < 0:
                return -1, True  # Return final sugar and death status
        return sim_sugar, False

    def simulate_invest_scenario(self, horizon):
        """Simulates future sugar if agent invests then forages."""
        if self.sugar < self.INVESTMENT_COST:
            return -1, True
        
        sim_sugar = self.sugar - self.INVESTMENT_COST
        expected_harvest = self.get_max_harvestable_sugar()
        current_sim_metabolism = self.metabolism_sugar
        
        for i in range(horizon):
            if i < self.INVESTMENT_DURATION:
                pass
            else:
                if i == self.INVESTMENT_DURATION:
                    current_sim_metabolism *= self.METABOLISM_REDUCTION_FACTOR
                sim_sugar += expected_harvest
            
            sim_sugar -= current_sim_metabolism
            if sim_sugar < 0:
                return -1, True

        return sim_sugar, False

    def step(self):
        """Main step logic for the agent."""
        if self.is_investing:
            self.investment_counter -= 1
            if self.investment_counter <= 0:
                self.metabolism_sugar *= self.METABOLISM_REDUCTION_FACTOR
                self.is_investing = False
        else:
            forage_utility, forage_death = self.simulate_forage_scenario(self.LOOK_AHEAD_HORIZON)
            invest_utility, invest_death = self.simulate_invest_scenario(self.LOOK_AHEAD_HORIZON)

            chosen_action = "FORAGE"
            if forage_death and not invest_death:
                chosen_action = "INVEST"
            elif not forage_death and invest_death:
                chosen_action = "FORAGE"
            elif not forage_death and not invest_death:
                if invest_utility > forage_utility:
                    chosen_action = "INVEST"
            
            if chosen_action == "INVEST":
                self.sugar -= self.INVESTMENT_COST
                self.is_investing = True
                self.investment_counter = self.INVESTMENT_DURATION
            else: # FORAGE
                self.move()
                self.eat()

        self.metabolize()
        self.maybe_die()
    # --- END of Functional Additions for Milestone 2 ---

    def move(self):
        """
        Function for the trader agent to find the best cell to move to.
        1. Identify all possible neighboring cells within its vision.
        2. Determine which move maximizes sugar intake (welfare).
        3. Find the closest of the best options.
        4. Move to the chosen cell.
        """
        # 1. Identify all possible moves (empty cells)
        neighboring_cells = [
            cell
            for cell in self.cell.get_neighborhood(self.vision, include_center=True)
            if cell.is_empty
        ]

        # 2. Determine which move maximizes welfare (total sugar after moving)
        welfares = [
            self.calculate_welfare(self.sugar + cell.sugar)
            for cell in neighboring_cells
        ]

        # 3. Find the closest best option
        if not welfares:
            # No empty cells to move to, stay put.
            return

        max_welfare = max(welfares)
        candidate_indices = [
            i for i, w in enumerate(welfares) if math.isclose(w, max_welfare)
        ]
        candidates = [neighboring_cells[i] for i in candidate_indices]

        # Find the minimum distance among the best candidates
        min_dist = min(get_distance(self.cell, cell) for cell in candidates)

        # Get all candidates that are at the minimum distance
        final_candidates = [
            cell
            for cell in candidates
            if math.isclose(get_distance(self.cell, cell), min_dist, rel_tol=1e-2)
        ]

        # 4. Move Agent
        self.cell = self.random.choice(final_candidates)

    def eat(self):
        """
        Agent harvests sugar from its current cell and metabolizes some sugar.
        """
        self.sugar += self.cell.sugar
        self.cell.sugar = 0
        # --- START of Functional Change for Milestone 2 ---
        # Metabolism is now handled separately in the step method
        # self.sugar -= self.metabolism_sugar
        # --- END of Functional Change for Milestone 2 ---

    # --- START of Functional Additions for Milestone 2 ---
    def metabolize(self):
        """Agent consumes sugar for metabolism."""
        self.sugar -= self.metabolism_sugar
    # --- END of Functional Additions for Milestone 2 ---
        
    def maybe_die(self):
        """
        Function to remove agents who have consumed all their sugar.
        """
        if self.is_starved():
            self.remove()