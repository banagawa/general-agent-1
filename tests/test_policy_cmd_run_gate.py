from __future__ import annotations

from policy.engine import PolicyEngine


def test_policy_engine_cmd_run_denies_non_allowlisted():
    pe = PolicyEngine()
    assert pe.is_allowed("CMD_RUN", {"argv": ["bash"]}) is False


def test_policy_engine_cmd_run_allows_python():
    pe = PolicyEngine()
    assert pe.is_allowed("CMD_RUN", {"argv": ["python", "--version"]}) is True
