from agent_core.loop import AgentLoop
from tools.gateway import ToolGateway

class Orchestrator:
    def __init__(self):
        self.gateway = ToolGateway()
        self.loop = AgentLoop(self.gateway)

    def handle(self, task: str) -> str:
        return self.loop.run(task)
