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

        if task.lower().startswith("update file:"):
            parts = task.split(":", 2)
            if len(parts) < 3:
                return "Usage: update file: <relative_path>: <new content>"

            rel_path = parts[1].strip()
            new_content = parts[2].strip()

            from sandbox.mounts import WORKSPACE_ROOT
            full_path = (WORKSPACE_ROOT / rel_path).resolve()

            try:
                diff = self.gateway.write_file(full_path, new_content)
                return f"Patch applied:\n{diff}"
            except Exception as e:
                return str(e)


        return f"[STUB] Agent received task: {task}"


