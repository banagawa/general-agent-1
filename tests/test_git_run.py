from __future__ import annotations

from pathlib import Path
import pytest

from policy.capabilities import issue_token

def _set_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))
    return workspace

def _make_gateway():
    from tools.gateway import ToolGateway  # noqa: WPS433
    return ToolGateway()

@pytest.fixture()
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path

def test_git_run_allows_status_without_token(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ws = _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()

    tok = issue_token(actions=["GIT_RUN"], ttl_seconds=120)
    init = gw.git_run(["git", "init"], cap_token_id=tok.id)
    assert init["ok"] is True
    assert init.get("exit_code") in (0, None)

    (ws / "x.txt").write_text("hi", encoding="utf-8")
    res = gw.git_run(["git", "status", "--porcelain"])
    assert res["ok"] is True
    assert res.get("exit_code") in (0, None)
    
def test_git_run_denies_push(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()
    res = gw.git_run(["git", "push"])
    assert res["ok"] is False
    assert res.get("denied") is True

def test_git_run_denies_commit_without_token(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()
    res = gw.git_run(["git", "commit", "-m", "x"])
    assert res["ok"] is False
    assert res.get("denied") is True

def test_git_run_allows_init_with_token(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()
    tok = issue_token(actions=["GIT_RUN"], ttl_seconds=120)
    res = gw.git_run(["git", "init"], cap_token_id=tok.id)
    assert res["ok"] is True
