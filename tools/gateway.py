from __future__ import annotations

import uuid
from pathlib import Path
from sandbox.mounts import get_workspace_root
from policy.engine import PolicyEngine
from tools.fs_tools import FileSystemTools
from audit.log import log_event
from policy.cmd_policy import validate_cmd_run
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
        tx_id = uuid.uuid4().hex
        # Sprint B Day 1: execution-phase transaction framing (logical only; no FS rollback).
        # Additive-only audit events; existing audit events remain unchanged.
        log_event("TRANSACTION_START", {
            "tx_id": tx_id,
            "tool": "CMD_RUN",
            "argv": list(argv),
            "timeout_seconds": int(timeout_seconds),
            "cap_token_id": cap_token_id,
        })

        argv_list = list(argv)

        try:
            # Capability enforcement (fail closed). Capability-model plans include CMD_RUN.
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
                log_event("TRANSACTION_ROLLBACK", {
                    "tx_id": tx_id,
                    "tool": "CMD_RUN",
                    "reason": "POLICY_DENIAL",
                    "detail": {"layer": "capability", "code": vr.reason},
                })
                return {"ok": False, "denied": True, "reason": vr.reason}

            # Existing Sprint A policy enforcement stays intact
            decision = validate_cmd_run(argv)
            if not decision.allowed:
                log_event("CMD_RUN_DENIED", {
                    "argv": argv_list,
                    "token_id": vr.token_id,
                    "decision": "deny",
                    "reason": decision.reason,
                })
                log_event("TRANSACTION_ROLLBACK", {
                    "tx_id": tx_id,
                    "tool": "CMD_RUN",
                    "reason": "POLICY_DENIAL",
                    "detail": {"layer": "cmd_policy", "code": decision.reason},
                })
                return {"ok": False, "denied": True, "reason": decision.reason}

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

            if res.get("timed_out"):
                log_event("TRANSACTION_ROLLBACK", {
                    "tx_id": tx_id,
                    "tool": "CMD_RUN",
                    "reason": "TIMEOUT",
                })
                return {"ok": True, **res}

            log_event("TRANSACTION_COMMIT", {
                "tx_id": tx_id,
                "tool": "CMD_RUN",
                "exit_code": res.get("exit_code"),
                "duration_ms": res.get("duration_ms"),
            })
            return {"ok": True, **res}
        except Exception as e:
            # Fail-closed: audit rollback for any unexpected exception path.
            log_event("TRANSACTION_ROLLBACK", {
                "tx_id": tx_id,
                "tool": "CMD_RUN",
                "reason": "UNEXPECTED_EXCEPTION",
                "detail": {"exc_type": type(e).__name__, "message": str(e)},
            })
            raise
