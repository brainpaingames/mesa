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
    A trader agent that can choose between foraging and investing.
    - Has a metabolism of sugar.
    - Harvests sugar to survive.
    - Can invest sugar to permanently reduce metabolism.
    """

    def __init__(self, model, cell, sugar=0, metabolism_sugar=0, vision=0):
        super().__init__(model)
        self.cell = cell
        self.sugar = sugar
        self.metabolism_sugar = metabolism_sugar
        self.vision = vision
        
        # Investment-related attributes
        self.is_investing = False
        self.investment_counter = 0

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
        # --- START of Functional Change ---
        # Use model-level parameters
        if (not self.model.enable_investment) or (self.sugar < self.model.investment_cost):
            return -1, True # Cannot afford or feature disabled, scenario is invalid
        
        sim_sugar = self.sugar - self.model.investment_cost
        expected_harvest = self.get_max_harvestable_sugar()
        current_sim_metabolism = self.metabolism_sugar
        
        for i in range(horizon):
            # Investment phase
            if i < self.model.investment_duration:
                pass  # No harvesting during investment
            # Post-investment phase
            else:
                # Benefit kicks in after investment is complete
                if i == self.model.investment_duration:
                    current_sim_metabolism *= self.model.metabolism_reduction_factor
                sim_sugar += expected_harvest
            
            sim_sugar -= current_sim_metabolism
            if sim_sugar < 0:
                return -1, True # Agent died during simulation

        return sim_sugar, False
        # --- END of Functional Change ---

    def step(self):
        """Main step logic for the agent."""
        # --- Handle ongoing investment first ---
        if self.is_investing:
            self.investment_counter -= 1
            if self.investment_counter <= 0:
                # --- START of Functional Change ---
                self.metabolism_sugar *= self.model.metabolism_reduction_factor
                # --- END of Functional Change ---
                self.is_investing = False
        
        else:
            # --- Step 1: Deliberate between Foraging and Investing ---
            # --- START of Functional Change ---
            horizon = self.model.agent_look_ahead_horizon
            forage_utility, forage_death = self.simulate_forage_scenario(horizon)
            invest_utility, invest_death = self.simulate_invest_scenario(horizon)
            # --- END of Functional Change ---

            chosen_action = "FORAGE"
            # Survival first
            if forage_death and not invest_death:
                chosen_action = "INVEST"
            elif not forage_death and invest_death:
                chosen_action = "FORAGE"
            # If both survive, maximize sugar
            elif not forage_death and not invest_death:
                if invest_utility > forage_utility:
                    chosen_action = "INVEST"
            
            # --- Step 2: Execute chosen action ---
            if chosen_action == "INVEST":
                # --- START of Functional Change ---
                self.sugar -= self.model.investment_cost
                self.is_investing = True
                self.investment_counter = self.model.investment_duration
                # --- END of Functional Change ---
            else: # FORAGE
                self.move()
                self.eat()

        # --- Step 3: Metabolize and possibly die ---
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

        # 4. Move Agent
        self.cell = self.random.choice(final_candidates)

    def eat(self):
        """
        Agent harvests sugar from its current cell.
        """
        self.sugar += self.cell.sugar
        self.cell.sugar = 0

    def metabolize(self):
        """Agent consumes sugar for metabolism."""
        self.sugar -= self.metabolism_sugar
        
    def maybe_die(self):
        """
        Function to remove agents who have consumed all their sugar.
        """
        if self.is_starved():
            self.remove()