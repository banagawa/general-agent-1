from __future__ import annotations

from pathlib import Path
from sandbox.mounts import get_workspace_root
from policy.engine import PolicyEngine
from tools.fs_tools import FileSystemTools
from audit.log import log_event
from tools.cmd_tools import run_cmd
from typing import Sequence, Dict, Any, Optional, List

from policy.capabilities import validate_token


class ToolGateway:
    def __init__(self):
        self.policy = PolicyEngine()
        self.fs = FileSystemTools()

    def search_files(self, query: str):
        ws_root = get_workspace_root()
        log_event("FS_SEARCH", {"query": query})

        results = self.fs.search(ws_root, query)

        allowed: List[Path] = []
        for path in results:
            if self.policy.is_allowed("FS_READ", path):
                allowed.append(path)
            else:
                log_event("DENY_SEARCH_RESULT", {"path": str(path)})

        return allowed

    def read_abs_path(self, path: Path):
        # Enforce policy for reads
        if not self.policy.is_allowed("FS_READ", path):
            log_event("DENY_READ", {"path": str(path)})
            raise PermissionError(f"Access denied: {path}")

        log_event("ALLOW_READ", {"path": str(path)})
        return self.fs.read(path)

    def write_file(self, path: Path, new_content: str, cap_token_id: Optional[str] = None):
        # Capability enforcement MUST happen at the ToolGateway boundary (fail closed).
        vr = validate_token(
            token_id=cap_token_id,
            action="FS_WRITE_PATCH",
            context={"path": str(path)},
        )
        if not vr.allowed:
            log_event("DENY_WRITE", {
                "path": str(path),
                "token_id": vr.token_id,
                "decision": "deny",
                "reason": vr.reason,
            })
            raise PermissionError(f"Write denied: {vr.reason}")

        # Policy still applies (system allowlist/constraints)
        if not self.policy.is_allowed("FS_WRITE_PATCH", path):
            log_event("DENY_WRITE", {
                "path": str(path),
                "token_id": vr.token_id,
                "decision": "deny",
                "reason": "policy",
            })
            raise PermissionError(f"Write denied: {path}")

        diff = self.fs.apply_patch(path, new_content)
        log_event("ALLOW_WRITE", {
            "path": str(path),
            "token_id": vr.token_id,
            "decision": "allow",
        })
        return diff
    def cmd_run(
        self,
        argv: Sequence[str],
        timeout_seconds: int = 10,
        cap_token_id: Optional[str] = None,
        ) -> Dict[str, Any]:
        argv_list = list(argv)

        # Capability enforcement (fail closed).
        vr = validate_token(
            token_id=cap_token_id,
            action="CMD_RUN",
            context={"argv": argv_list},
        )
        if not vr.allowed:
            log_event("CMD_RUN_DENIED", {
                "argv": argv_list,
                "token_id": vr.token_id,
                "decision": "deny",
                "reason": vr.reason,
            })
            return {"ok": False, "denied": True, "reason": vr.reason}

        # Policy enforcement: MUST route through PolicyEngine gate (Architecture Contract).
        if not self.policy.is_allowed("CMD_RUN", {"argv": argv_list}):
            reason = "disallowed"
            if hasattr(self.policy, "explain_denial"):
                reason = self.policy.explain_denial("CMD_RUN", {"argv": argv_list}) or "disallowed"

            log_event(
                "CMD_RUN_DENIED",
                {
                    "argv": argv_list,
                    "token_id": vr.token_id,
                    "decision": "deny",
                    "reason": reason,
                },
            )
            return {"ok": False, "denied": True, "reason": reason}
        
        ws_root = get_workspace_root()
        res = run_cmd(argv=argv_list, workspace_root=ws_root, timeout=int(timeout_seconds))

        log_event("CMD_RUN_EXECUTED", {
            "argv": argv_list,
            "cwd": str(ws_root),
            "timeout": int(timeout_seconds),
            "exit_code": res.get("exit_code"),
            "duration_ms": res.get("duration_ms"),
            "stdout_truncated": res.get("stdout_truncated"),
            "stderr_truncated": res.get("stderr_truncated"),
            "timed_out": res.get("timed_out"),
            "token_id": vr.token_id,
            "decision": "allow",
        })
        return {"ok": True, **res}
        
    def git_run(
        self,
        argv: Sequence[str],
        timeout_seconds: int = 10,
        cap_token_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        argv_list = list(argv)

        # classify mutating vs read-only (Sprint C)
        sub = ""
        if len(argv_list) >= 2 and isinstance(argv_list[1], str):
            sub = argv_list[1].strip().lower()

        is_mutation = sub in {"init", "add", "commit"}

        # Token-gate ONLY mutations (read-only allowed without token)
        vr = None
        if is_mutation:
            vr = validate_token(
                token_id=cap_token_id,
                action="GIT_RUN",
                context={"argv": argv_list},
            )
            if not vr.allowed:
                log_event("GIT_RUN_DENIED", {
                    "argv": argv_list,
                    "token_id": getattr(vr, "token_id", None),
                    "decision": "deny",
                    "reason": getattr(vr, "reason", "token_denied"),
                })
                return {"ok": False, "denied": True, "reason": getattr(vr, "reason", "token_denied")}

        # Policy gate (single enforcement spine)
        if not self.policy.is_allowed("GIT_RUN", {"argv": argv_list}):
            reason = "disallowed"
            if hasattr(self.policy, "explain_denial"):
                reason = self.policy.explain_denial("GIT_RUN", {"argv": argv_list}) or "disallowed"

            log_event("GIT_RUN_DENIED", {
                "argv": argv_list,
                "token_id": getattr(vr, "token_id", None) if vr else None,
                "decision": "deny",
                "reason": reason,
            })
            return {"ok": False, "denied": True, "reason": reason}

        ws_root = get_workspace_root()
        res = run_cmd(argv=argv_list, workspace_root=ws_root, timeout=int(timeout_seconds))

        log_event("GIT_RUN_EXECUTED", {
            "argv": argv_list,
            "cwd": str(ws_root),
            "timeout": int(timeout_seconds),
            "exit_code": res.get("exit_code"),
            "duration_ms": res.get("duration_ms"),
            "stdout_truncated": res.get("stdout_truncated"),
            "stderr_truncated": res.get("stderr_truncated"),
            "timed_out": res.get("timed_out"),
            "token_id": getattr(vr, "token_id", None) if vr else None,
            "decision": "allow",
        })
        return {"ok": True, **res}
