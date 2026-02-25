from __future__ import annotations

import os
from pathlib import Path
import pytest
from policy.capabilities import issue_token

def _set_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """
    Force the agent workspace to a temp directory for the test run.
    We set both env vars since earlier iterations used different names.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))  # if your mounts.py uses this
    return workspace


def _make_gateway():
    """
    Import inside function so env vars are applied before mounts/policy read them.
    """
    from tools.gateway import ToolGateway  # noqa: WPS433

    return ToolGateway()


@pytest.fixture()
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Ensure audit files (.audit/...) do not land in your real repo during tests.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_cmd_run_denies_non_allowlisted(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()

    # ---- CHANGE THIS LINE if your gateway method name differs ----
    tok = issue_token(actions=["CMD_RUN"], ttl_seconds=120)
    res = gw.cmd_run(["bash"], cap_token_id=tok.id)
    # should be denied by allowlist
    # --------------------------------------------------------------

    assert isinstance(res, dict)
    assert res.get("ok") is False
    assert res.get("denied") is True
    assert res.get("reason")  # should include something like cmd_not_allowlisted


def test_cmd_run_denies_disallowed_tokens(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()
    tok = issue_token(actions=["CMD_RUN"], ttl_seconds=120)
    res = gw.cmd_run(["git", "status;rm", "-rf", "."], cap_token_id=tok.id)  # token should trigger deny

    assert isinstance(res, dict)
    assert res.get("allowed") is False or res.get("denied") is True
    assert "disallowed" in (res.get("reason", "") + res.get("error", "")).lower()


def test_cmd_run_allows_python_version(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()
    tok = issue_token(actions=["CMD_RUN"], ttl_seconds=120)
    res = gw.cmd_run(["python", "--version"], cap_token_id=tok.id)

    assert isinstance(res, dict)
    assert res.get("denied") is not True
    assert res.get("exit_code") in (0, None)  # None only if you wrap deny differently
    # Some Python builds print version to stderr, some to stdout
    out = (res.get("stdout") or "") + (res.get("stderr") or "")
    assert "python" in out.lower()


def test_cmd_run_forces_cwd_to_workspace(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    workspace = _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()

    # Print cwd from inside the command
    tok = issue_token(actions=["CMD_RUN"], ttl_seconds=120)
    res = gw.cmd_run(["python", "-c", "import os; print(os.getcwd())"], cap_token_id=tok.id)

    assert res.get("denied") is not True
    cwd_reported = (res.get("stdout") or "").strip()

    # Normalize both sides for Windows/POSIX slashes and case
    norm_reported = os.path.normcase(os.path.normpath(cwd_reported))
    norm_expected = os.path.normcase(os.path.normpath(str(workspace)))
    assert norm_reported == norm_expected


def test_cmd_run_truncates_output(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()

    # 200k chars should exceed your 64KB cap
    tok = issue_token(actions=["CMD_RUN"], ttl_seconds=120)
    res = gw.cmd_run(["python", "-c", "print('A' * 200000)"], cap_token_id=tok.id)

    assert res.get("denied") is not True
    assert res.get("stdout_truncated") is True
    assert isinstance(res.get("stdout"), str)
    assert len(res["stdout"].encode("utf-8", errors="ignore")) <= 64 * 1024


def test_cmd_run_times_out(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()

    # If your gateway exposes timeout_seconds, use it.
    # Otherwise, adjust to whatever your gateway signature is.
    tok = issue_token(actions=["CMD_RUN"], ttl_seconds=120)
    res = gw.cmd_run(["python", "-c", "import time; time.sleep(2)"], timeout_seconds=1, cap_token_id=tok.id)

    assert res.get("denied") is not True
    assert res.get("timed_out") is True
    assert res.get("exit_code") is None
