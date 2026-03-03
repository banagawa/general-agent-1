from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Sequence

from sandbox.mounts import WORKSPACE_ROOT

from policy.cmd_policy import validate_cmd_run

DENY_PATTERNS = [".env", "secrets", "credentials"]


class PolicyEngine:
    def is_allowed(self, action: str, target: Any) -> bool:
        """
        Single policy enforcement gate.

        - For FS_* actions, target must be a Path.
        - For CMD_RUN, target must be a dict like {"argv": Sequence[str]}.

        Fail-closed on any unexpected input or exception.
        """
        try:
            if action == "CMD_RUN":
                return self._is_allowed_cmd_run(target)

            # Default: filesystem-style policy
            if not isinstance(target, Path):
                return False

            return self._is_allowed_fs(action, target)

        except Exception:
            # Fail closed
            return False

    def _is_allowed_cmd_run(self, target: Any) -> bool:
        if not isinstance(target, dict):
            return False

        argv = target.get("argv")
        if not isinstance(argv, (list, tuple)):
            return False

        decision = validate_cmd_run(argv)  # Sprint A policy
        return bool(decision.allowed)

    def _is_allowed_fs(self, action: str, path: Path) -> bool:
        try:
            resolved = path.resolve()
        except Exception:
            return False

        # Must be inside workspace
        try:
            resolved.relative_to(WORKSPACE_ROOT)
        except ValueError:
            return False

        # Basic deny patterns
        s = str(resolved)
        for pattern in DENY_PATTERNS:
            if pattern in s:
                return False

        # Allowlist of supported filesystem actions
        if action not in ("FS_READ", "FS_SEARCH", "FS_WRITE_PATCH"):
            return False

        return True
    def explain_denial(self, action: str, target: Any) -> str:
        """
        Best-effort denial explanation for audit/user-facing errors.
        Must be fail-closed and never raise.
        """
        try:
            if action == "CMD_RUN":
                if not isinstance(target, dict):
                    return "disallowed: invalid_context"
                argv = target.get("argv")
                if not isinstance(argv, (list, tuple)):
                    return "disallowed: invalid_argv"
                decision = validate_cmd_run(argv)
                if decision.allowed:
                    return ""  # not denied
                # Preserve cmd_policy reason semantics if present
                r = getattr(decision, "reason", None)
                if r:
                    return f"disallowed: {r}"
                return "disallowed: cmd_policy"
            return "disallowed"
        except Exception:
            return "disallowed"
