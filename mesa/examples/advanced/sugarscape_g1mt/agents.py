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

    def __init__(self, model, cell, sugar=0, metabolism_sugar=0, vision=0):
        super().__init__(model)
        self.cell = cell
        self.sugar = sugar
        self.metabolism_sugar = metabolism_sugar
        self.vision = vision

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

    ######################################################################
    #                      MAIN AGENT FUNCTIONS                          #
    ######################################################################

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
        self.sugar -= self.metabolism_sugar

    def maybe_die(self):
        """
        Function to remove agents who have consumed all their sugar.
        """
        if self.is_starved():
            self.remove()