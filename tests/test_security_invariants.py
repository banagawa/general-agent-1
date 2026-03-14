from __future__ import annotations

import pytest

from agent_core.security_invariants import assert_security_invariants


def test_assert_security_invariants_allows_safe_path() -> None:
    assert_security_invariants(shell=False, direct_tool_bypass=False)


def test_assert_security_invariants_denies_shell_true() -> None:
    with pytest.raises(RuntimeError, match="shell=True is forbidden"):
        assert_security_invariants(shell=True, direct_tool_bypass=False)


def test_assert_security_invariants_denies_direct_tool_bypass() -> None:
    with pytest.raises(RuntimeError, match="direct tool bypass is forbidden"):
        assert_security_invariants(shell=False, direct_tool_bypass=True)


def test_assert_security_invariants_denies_both_violations() -> None:
    with pytest.raises(RuntimeError):
        assert_security_invariants(shell=True, direct_tool_bypass=True)
