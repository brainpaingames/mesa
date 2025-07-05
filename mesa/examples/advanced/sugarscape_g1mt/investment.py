class InvestmentOpportunity:
    def __init__(self, name, requirements, cost, reward):
        self.name = name
        self.requirements = requirements
        self.cost = cost
        self.reward = reward

    def is_available(self, agent):
        pass

    def calculate_utility(self, agent, horizon):
        pass

    def apply_reward_to(self, capabilities_dict):
        capabilities_dict.update(self.reward)