from tools.gateway import ToolGateway
from sandbox.mounts import WORKSPACE_ROOT

class AgentLoop:
    def __init__(self,gateway):
        self.gateway = gateway

    def run(self, task: str) -> str:
        task = task.strip()

        if task.lower().startswith("find and summarize:"):
            query = task.split(":", 1)[1].strip()
            paths = self.gateway.search_files(query)

            if not paths:
                return f"No matches found for: {query}"

            out = [f"Top matches for '{query}':"]
            for p in paths[:3]:
                # p is a Path from fs_tools.search
                content = self.gateway.read_abs_path(p)
                snippet = content[:400].replace("\n", " ")
                relative = p.relative_to(WORKSPACE_ROOT)
                out.append(f"- {relative}: {snippet}")

            return "\n".join(out)

        if task.lower().startswith("search:"):
            query = task.split(":", 1)[1].strip()
            paths = self.gateway.search_files(query)
            return "\n".join(str(p) for p in paths[:20]) if paths else "No matches."

        return f"[STUB] Agent received task: {task}"

