from __future__ import annotations

from pathlib import Path
from sandbox.mounts import get_workspace_root
from policy.engine import PolicyEngine
from tools.fs_tools import FileSystemTools
from audit.log import log_event
from policy.revocations import writes_revoked
from policy.cmd_policy import validate_cmd_run
from tools.cmd_tools import run_cmd
from typing import Sequence, Dict, Any, Optional, List

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

    def cmd_run(self, argv: Sequence[str], timeout_seconds: int = 10) -> Dict[str, Any]:
        decision = validate_cmd_run(argv)
        argv_list = list(argv)
        if not decision.allowed:
            log_event("CMD_RUN_DENIED", {"argv": argv_list, "reason": decision.reason})
            return {"ok": False, "denied": True, "reason": decision.reason}

        res = run_cmd(argv=argv_list, workspace_root= get_workspace_root(), timeout=int(timeout_seconds))
        log_event("CMD_RUN_EXECUTED", {
            "argv": argv_list,
            "cwd": str(get_workspace_root),
            "timeout": timeout_seconds,
            "exit_code": res.get("exit_code"),
            "duration_ms": res.get("duration_ms"),
            "stdout_truncated": res.get("stdout_truncated"),
            "stderr_truncated": res.get("stderr_truncated"),
            "timed_out": res.get("timed_out"),
        })
        return {"ok": True, **res}
