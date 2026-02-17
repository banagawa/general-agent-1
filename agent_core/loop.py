class AgentLoop:
    def __init__(self,gateway):
        self.gateway = gateway


    def run(self, task: str) -> str:
        return f"[STUB] Agent received task: {task}"
