from pathlib import Path
from sandbox.mounts import WORKSPACE_ROOT
from policy.engine import PolicyEngine
from tools.fs_tools import FileSystemTools
from audit.log import log_event
from policy.revocations import writes_revoked
class ToolGateway:
    def __init__(self):
        self.policy = PolicyEngine()
        self.fs = FileSystemTools()

    def search_files(self, query: str):
        log_event("FS_SEARCH", query)
        return self.fs.search(WORKSPACE_ROOT, query)
        allowed = []
        for path in results:
            if self.policy.is_allowed("FS_READ", path):
                allowed.append(path)
            else:
                log_event("DENY_SEARCH_RESULT", str(path))

        return allowed

    def read_abs_path(self, path: Path):
        # Enforce policy for reads
        if not self.policy.is_allowed("FS_READ", path):
            log_event("DENY_READ", str(path))
            raise PermissionError(f"Access denied: {path}")

        log_event("ALLOW_READ", str(path))
        return self.fs.read(path)

    def write_file(self, path: Path, new_content: str):

        if writes_revoked():
            log_event("DENY_WRITE", f"{path} reason=revoked")
            raise PermissionError("Write denied: writes are revoked")

        if not self.policy.is_allowed("FS_WRITE_PATCH", path):
            log_event("DENY_WRITE", str(path))
            raise PermissionError(f"Write denied: {path}")

        diff = self.fs.apply_patch(path, new_content)
        log_event("ALLOW_WRITE", str(path))
        return diff
