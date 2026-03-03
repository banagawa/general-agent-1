from __future__ import annotations

from policy.engine import PolicyEngine

def test_policy_engine_git_run_denies_remote():
    pe = PolicyEngine()
    assert pe.is_allowed("GIT_RUN", {"argv": ["git", "push"]}) is False

def test_policy_engine_git_run_allows_status():
    pe = PolicyEngine()
    assert pe.is_allowed("GIT_RUN", {"argv": ["git", "status"]}) is True
def test_policy_engine_git_run_denies_git_dir_override():
    pe = PolicyEngine()
    assert pe.is_allowed("GIT_RUN", {"argv": ["git", "--git-dir=foo", "status"]}) is False
