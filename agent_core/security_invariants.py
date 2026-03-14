from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityInvariants:
    execution_choke_point: bool = True
    deny_by_default: bool = True
    workspace_boundary: bool = True
    patch_only_mutation: bool = True
    append_only_audit: bool = True
    fail_closed: bool = True
    shell_passthrough_forbidden: bool = True


INVARIANTS = SecurityInvariants()


def assert_security_invariants(*, shell: bool | None = None, direct_tool_bypass: bool = False) -> None:
    if direct_tool_bypass:
        raise RuntimeError("Security invariant violation: direct tool bypass is forbidden")

    if shell is True:
        raise RuntimeError("Security invariant violation: shell=True is forbidden")
