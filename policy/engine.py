from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence
from sandbox.mounts import get_workspace_root
from policy.cmd_policy import validate_cmd_run
from policy.git_policy import validate_git_run

DENY_PATTERNS = [".env", "secrets", "credentials"]


class PolicyEngine:
    def is_allowed(self, action: str, target: Any) -> bool:
        """
        Single policy enforcement gate.

        - For FS_* actions, target must be a Path.
        - For CMD_RUN, target must be {"argv": Sequence[str]}.
        - For GIT_RUN, target must be {"argv": Sequence[str]}.
        """
        try:
            if action == "CMD_RUN":
                return self._is_allowed_cmd_run(target)
            if action == "GIT_RUN":
                return self._is_allowed_git_run(target)

            if not isinstance(target, Path):
                return False
            return self._is_allowed_fs(action, target)
        except Exception:
            return False

    def _is_allowed_cmd_run(self, target: Any) -> bool:
        if not isinstance(target, dict):
            return False
        argv = target.get("argv")
        if not isinstance(argv, (list, tuple)):
            return False
        return bool(validate_cmd_run(argv).allowed)

    def _is_allowed_git_run(self, target: Any) -> bool:
        if not isinstance(target, dict):
            return False
        argv = target.get("argv")
        if not isinstance(argv, (list, tuple)):
            return False
        ws = get_workspace_root()
        return bool(validate_git_run(argv, ws).allowed)

    def _is_allowed_fs(self, action: str, path: Path) -> bool:
        try:
            resolved = path.resolve()
        except Exception:
            return False

        workspace_root = get_workspace_root()

        try:
            resolved.relative_to(workspace_root)
        except ValueError:
            return False

        s = str(resolved)
        for pattern in DENY_PATTERNS:
            if pattern in s:
                return False

        if action not in ("FS_READ", "FS_SEARCH", "FS_WRITE_PATCH", "FS_EDIT_PATCH"):
            return False

        return True

    def explain_denial(self, action: str, target: Any) -> str:
        try:
            if action == "CMD_RUN":
                if not isinstance(target, dict):
                    return "disallowed: invalid_context"
                argv = target.get("argv")
                if not isinstance(argv, (list, tuple)):
                    return "disallowed: invalid_argv"
                d = validate_cmd_run(argv)
                return "" if d.allowed else f"disallowed: {getattr(d, 'reason', 'cmd_policy')}"

            if action == "GIT_RUN":
                if not isinstance(target, dict):
                    return "disallowed: invalid_context"
                argv = target.get("argv")
                if not isinstance(argv, (list, tuple)):
                    return "disallowed: invalid_argv"
                ws = get_workspace_root()
                d = validate_git_run(argv, ws)
                return "" if d.allowed else f"disallowed: {getattr(d, 'reason', 'git_policy')}"

            return "disallowed"
        except Exception:
            return "disallowed"
