from __future__ import annotations

import uuid
import time
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

    def _tx_meta(self, tx_id: str, tool: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        m: Dict[str, Any] = {
            "tx_id": tx_id,                 # required by tests
            "transaction_id": tx_id,        # optional (ok to keep)
            "tool": tool,
        }
        if extra:
            m.update(extra)
        return m

    def _tx_start(self, tx_id: str, tool: str, meta: Dict[str, Any]) -> float:
        log_event("TRANSACTION_START", self._tx_meta(tx_id, tool, meta))
        return time.monotonic()

    def _tx_commit(self, tx_id: str, tool: str, started_at: float, meta: Optional[Dict[str, Any]] = None) -> None:
        dur_ms = int((time.monotonic() - started_at) * 1000)
        base: Dict[str, Any] = {"duration_ms": dur_ms}
        if meta:
            base.update(meta)
        log_event("TRANSACTION_COMMIT", self._tx_meta(tx_id, tool, base))

    def _tx_rollback(
        self,
        tx_id: str,
        tool: str,
        started_at: float,
        rollback_reason: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        dur_ms = int((time.monotonic() - started_at) * 1000)
        base: Dict[str, Any] = {
            "duration_ms": dur_ms,
            "rollback_reason": rollback_reason,
            "reason": rollback_reason
            }
        if meta:
            base.update(meta)
        log_event("TRANSACTION_ROLLBACK", self._tx_meta(tx_id, tool, base))

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
        # Sprint B: execution-phase transaction framing (logical only; no FS rollback).
        # Additive-only audit events; existing audit events remain unchanged.

        tx_id = str(uuid.uuid4())
        started_at = self._tx_start(
            tx_id,
            "FS_WRITE_PATCH",
            {
                "path": str(path),
                "cap_token_id": cap_token_id,
            },
        )

        try:
            # Capability enforcement MUST happen at the ToolGateway boundary (fail closed).
            vr = validate_token(
                token_id=cap_token_id,
                action="FS_WRITE_PATCH",
                context={"path": str(path)},
            )
            if not vr.allowed:
                log_event(
                    "DENY_WRITE",
                    {
                        "path": str(path),
                        "token_id": vr.token_id,
                        "decision": "deny",
                        "reason": vr.reason,
                    },
                )
                self._tx_rollback(
                    tx_id,
                    "FS_WRITE_PATCH",
                    started_at,
                    rollback_reason="POLICY_DENIAL",
                    meta={"layer": "capability", "code": vr.reason, "token_id": vr.token_id, "path": str(path)},
                )
                raise PermissionError(f"Write denied: {vr.reason}")

            # Policy still applies (system allowlist/constraints)
            if not self.policy.is_allowed("FS_WRITE_PATCH", path):
                log_event(
                    "DENY_WRITE",
                    {
                        "path": str(path),
                        "token_id": vr.token_id,
                        "decision": "deny",
                        "reason": "policy",
                    },
                )
                self._tx_rollback(
                    tx_id,
                    "FS_WRITE_PATCH",
                    started_at,
                    rollback_reason="POLICY_DENIAL",
                    meta={"layer": "policy", "code": "policy", "token_id": vr.token_id, "path": str(path)},
                )
                raise PermissionError(f"Write denied: {path}")

            diff = self.fs.apply_patch(path, new_content)

            log_event(
                "ALLOW_WRITE",
                {
                    "path": str(path),
                    "token_id": vr.token_id,
                    "decision": "allow",
                },
            )

            self._tx_commit(
                tx_id,
                "FS_WRITE_PATCH",
                started_at,
                meta={"token_id": vr.token_id, "path": str(path)},
            )
            return diff

        except PermissionError:
            # Already audited + rollbacked above for policy/capability denials.
            raise
        except Exception as e:
            # Fail-closed: audit rollback for any unexpected exception path.
            self._tx_rollback(
                tx_id,
                "FS_WRITE_PATCH",
                started_at,
                rollback_reason="UNEXPECTED_EXCEPTION",
                meta={"exc_type": type(e).__name__, "message": str(e), "path": str(path)},
            )
            raise

    def _cmd_run_deny(
        self,
        *,
        tx_id: str,
        started_at: float,
        argv_list: List[str],
        token_id: Optional[str],
        layer: str,
        code: str,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Single deny path for CMD_RUN:
        - Emits existing CMD_RUN_DENIED event (additive meta only)
        - Emits TRANSACTION_ROLLBACK with standardized meta
        - Returns a stable dict shape for callers/tests
        """
        log_event(
            "CMD_RUN_DENIED",
            {
                "argv": argv_list,
                "token_id": token_id,
                "decision": "deny",
                "reason": code,
                "layer": layer,
                "message": message,
            },
        )

        self._tx_rollback(
            tx_id,
            "CMD_RUN",
            started_at,
            rollback_reason="POLICY_DENIAL",
            meta={
                "layer": layer,
                "code": code,
                "token_id": token_id,
                "message": message,
            },
        )

        return {"ok": False, "denied": True, "reason": code}

    def cmd_run(
        self,
        argv: Sequence[str],
        timeout_seconds: int = 10,
        cap_token_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sprint B: execution-phase transaction framing (logical only; no FS rollback).
        Additive-only audit events; existing audit events remain (but can add meta fields).
        """
        tx_id = str(uuid.uuid4())
        argv_list = list(argv)

        started_at = self._tx_start(
            tx_id,
            "CMD_RUN",
            {
                "argv": argv_list,
                "timeout_seconds": int(timeout_seconds),
                "cap_token_id": cap_token_id,
            },
        )

        try:
            # 1) Capability enforcement (fail closed). Reason codes are from validate_token spec.
            vr = validate_token(
                token_id=cap_token_id,
                action="CMD_RUN",
                context={"argv": argv_list},
            )
            if not vr.allowed:
                return self._cmd_run_deny(
                    tx_id=tx_id,
                    started_at=started_at,
                    argv_list=argv_list,
                    token_id=vr.token_id,
                    layer="capability",
                    code=str(vr.reason or "DENIED"),
                )

            # 2) Existing cmd policy enforcement stays intact; we treat it as a policy denial.
            decision = validate_cmd_run(argv_list)
            if not decision.allowed:
                return self._cmd_run_deny(
                    tx_id=tx_id,
                    started_at=started_at,
                    argv_list=argv_list,
                    token_id=vr.token_id,
                    layer="cmd_policy",
                    code=str(decision.reason or "DENIED"),
                )

            # 3) Execute inside workspace root.
            ws_root = get_workspace_root()
            res = run_cmd(argv=argv_list, workspace_root=ws_root, timeout=int(timeout_seconds))

            log_event(
                "CMD_RUN_EXECUTED",
                {
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
                },
            )

            # Timeout is a rollback trigger in Sprint B.
            if res.get("timed_out"):
                self._tx_rollback(
                    tx_id,
                    "CMD_RUN",
                    started_at,
                    rollback_reason="TIMEOUT",
                    meta={"token_id": vr.token_id},
                )
                return {"ok": True, **res}

            self._tx_commit(
                tx_id,
                "CMD_RUN",
                started_at,
                meta={
                    "exit_code": res.get("exit_code"),
                    "duration_ms": res.get("duration_ms"),
                    "token_id": vr.token_id,
                },
            )
            return {"ok": True, **res}

        except Exception as e:
            # Unexpected exception is a rollback trigger in Sprint B.
            self._tx_rollback(
                tx_id,
                "CMD_RUN",
                started_at,
                rollback_reason="UNEXPECTED_EXCEPTION",
                meta={"exc_type": type(e).__name__, "message": str(e)},
            )
            raise
