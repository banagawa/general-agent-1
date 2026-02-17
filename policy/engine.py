class PolicyEngine:
    def is_allowed(self, action: str, path: str = None) -> bool:
        # Day 1: deny everything
        return False
