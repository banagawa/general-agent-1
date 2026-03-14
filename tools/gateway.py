from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from audit.log import log_event
from policy.capabilities import validate_token
from policy.engine import PolicyEngine
from sandbox.mounts import get_workspace_root
from tools.cmd_tools import run_cmd
from tools.fs_tools import FileSystemTools
from agent_core.security_invariants import assert_security_invariants

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
        if not self.policy.is_allowed("FS_READ", path):
            log_event("DENY_READ", {"path": str(path)})
            raise PermissionError(f"Access denied: {path}")

        log_event("ALLOW_READ", {"path": str(path)})
        return self.fs.read(path)

    def write_file(
        self,
        path: Path,
        new_content: str,
        cap_token_id: Optional[str] = None,
    ):
        assert_security_invariants(direct_tool_bypass=False)
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
            raise PermissionError(f"Write denied: {vr.reason}")

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
        return diff

    def patch_apply(
        self,
        path: Path | str,
        new_content: str,
        cap_token_id: Optional[str] = None,
    ):
        resolved_path = Path(path)
        return self.write_file(
            path=resolved_path,
            new_content=new_content,
            cap_token_id=cap_token_id,
        )

    def cmd_run(
        self,
        argv: Sequence[str],
        timeout_seconds: int = 10,
        cap_token_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        assert_security_invariants(shell=False, direct_tool_bypass=False)
        argv_list = list(argv)

        vr = validate_token(
            token_id=cap_token_id,
            action="CMD_RUN",
            context={"argv": argv_list},
        )
        if not vr.allowed:
            log_event(
                "CMD_RUN_DENIED",
                {
                    "argv": argv_list,
                    "token_id": vr.token_id,
                    "decision": "deny",
                    "reason": vr.reason,
                },
            )
            return {"ok": False, "denied": True, "reason": vr.reason}

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
        res = run_cmd(
            argv=argv_list,
            workspace_root=ws_root,
            timeout=int(timeout_seconds),
        )

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
        return {"ok": True, **res}

    def test_run(
        self,
        argv: Sequence[str],
        timeout_seconds: int = 30,
        cap_token_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.cmd_run(
            argv=argv,
            timeout_seconds=timeout_seconds,
            cap_token_id=cap_token_id,
        )

    def git_run(
        self,
        argv: Sequence[str],
        timeout_seconds: int = 10,
        cap_token_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        assert_security_invariants(direct_tool_bypass=False)
        argv_list = list(argv)

        sub = ""
        if len(argv_list) >= 2 and isinstance(argv_list[1], str):
            sub = argv_list[1].strip().lower()

        is_mutation = sub in {"init", "add", "commit"}

        vr = None
        if is_mutation:
            vr = validate_token(
                token_id=cap_token_id,
                action="GIT_RUN",
                context={"argv": argv_list},
            )
            if not vr.allowed:
                log_event(
                    "GIT_RUN_DENIED",
                    {
                        "argv": argv_list,
                        "token_id": getattr(vr, "token_id", None),
                        "decision": "deny",
                        "reason": getattr(vr, "reason", "token_denied"),
                    },
                )
                return {
                    "ok": False,
                    "denied": True,
                    "reason": getattr(vr, "reason", "token_denied"),
                }

        if not self.policy.is_allowed("GIT_RUN", {"argv": argv_list}):
            reason = "disallowed"
            if hasattr(self.policy, "explain_denial"):
                reason = self.policy.explain_denial("GIT_RUN", {"argv": argv_list}) or "disallowed"

            log_event(
                "GIT_RUN_DENIED",
                {
                    "argv": argv_list,
                    "token_id": getattr(vr, "token_id", None) if vr else None,
                    "decision": "deny",
                    "reason": reason,
                },
            )
            return {"ok": False, "denied": True, "reason": reason}

        ws_root = get_workspace_root()
        res = run_cmd(
            argv=argv_list,
            workspace_root=ws_root,
            timeout=int(timeout_seconds),
        )

        log_event(
            "GIT_RUN_EXECUTED",
            {
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
            },
        )
        return {"ok": True, **res}
