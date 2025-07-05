class InvestmentOpportunity:
    def __init__(self, name, requirements, cost, reward):
        self.name = name
        self.requirements = requirements
        self.cost = cost
        self.reward = reward

    def is_available(self, agent):
        return self.requirements["prerequisites"].issubset(agent.completed_investment_names)

    def calculate_utility(self, agent, horizon):
        sim_sugar = agent.sugar
        duration = self.cost["duration"]
        metabolism_rate = self.cost["metabolism_during_investment"]

        # 1. Simulate the cost period (investment duration)
        for _ in range(duration):
            sim_sugar -= metabolism_rate
            if sim_sugar <= 0:
                return -1, True  # Agent dies during investment

        # 2. Simulate the reward period (rest of the horizon)
        # Optimistic forecast: assume agent finds the best possible spot for its new skills
        future_capabilities = self.reward
        future_multipliers = future_capabilities["harvest_multipliers"]
        
        # Find the best possible harvest with the new multipliers
        # Assumes max capacity of a cell is its index in the multiplier list
        # and that a cell is fully stocked (sugar == capacity)
        potential_harvests = [i * m for i, m in enumerate(future_multipliers)]
        expected_harvest = max(potential_harvests) if potential_harvests else 0
        
        future_metabolism = future_capabilities["metabolism_sugar"]
        
        for _ in range(horizon - duration):
            sim_sugar += expected_harvest
            sim_sugar -= future_metabolism
            if sim_sugar <= 0:
                return -1, True # Agent dies after investment

        return sim_sugar, False

    def apply_reward_to(self, capabilities_dict):
        capabilities_dict.update(self.reward)