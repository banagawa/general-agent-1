from agent_core.loop import AgentLoop


class Orchestrator:
    def __init__(self):
        self.loop = AgentLoop()

    def handle(self, task: str) -> str:
        return self.loop.run(task)
