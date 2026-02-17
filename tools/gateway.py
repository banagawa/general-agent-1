from policy.engine import PolicyEngine
from audit.log import log_event
from sandbox.mounts import get_workspace_root


class ToolGateway:
    def __init__(self):
        self.policy = PolicyEngine()
        self.workspace_root = get_workspace_root()

    def search_files(self, query: str):
        log_event(f"SEARCH requested: {query}")
        # Real implementation tomorrow
        return []

    def read_file(self, path: str):
        log_event(f"READ requested: {path}")
        # Real implementation tomorrow
        return "[STUB] read_file not implemented yet"
