from __future__ import annotations

from pathlib import Path

from tools import gateway as gateway_module
from tools.gateway import ToolGateway


class Allowed:
    allowed = True
    reason = ""
    token_id = None


def _fake_run_result() -> dict:
    return {
        "exit_code": 0,
        "duration_ms": 1,
        "stdout": "",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "timed_out": False,
    }


def test_test_run_allows_workspace_cwd(monkeypatch) -> None:
    calls = {}

    monkeypatch.setattr(gateway_module, "validate_token", lambda **_: Allowed())
    monkeypatch.setattr(gateway_module, "get_workspace_root", lambda: Path("WORKSPACE"))
    monkeypatch.setattr(gateway_module, "get_app_root", lambda: Path("APP"))

    def fake_run_cmd(*, argv, workspace_root, timeout):
        calls["workspace_root"] = workspace_root
        return _fake_run_result()

    monkeypatch.setattr(gateway_module, "run_cmd", fake_run_cmd)

    result = ToolGateway().test_run(
        argv=["python", "-m", "pytest", "-q"],
        timeout_seconds=10,
        cwd="workspace",
    )

    assert result["ok"] is True
    assert calls["workspace_root"] == Path("WORKSPACE")


def test_test_run_allows_app_cwd(monkeypatch) -> None:
    calls = {}

    monkeypatch.setattr(gateway_module, "validate_token", lambda **_: Allowed())
    monkeypatch.setattr(gateway_module, "get_workspace_root", lambda: Path("WORKSPACE"))
    monkeypatch.setattr(gateway_module, "get_app_root", lambda: Path("APP"))

    def fake_run_cmd(*, argv, workspace_root, timeout):
        calls["workspace_root"] = workspace_root
        return _fake_run_result()

    monkeypatch.setattr(gateway_module, "run_cmd", fake_run_cmd)

    result = ToolGateway().test_run(
        argv=["python", "-m", "pytest", "-q"],
        timeout_seconds=10,
        cwd="app",
    )

    assert result["ok"] is True
    assert calls["workspace_root"] == Path("APP")


def test_test_run_denies_unknown_cwd() -> None:
    result = ToolGateway().test_run(
        argv=["python", "-m", "pytest", "-q"],
        timeout_seconds=10,
        cwd="somewhere_else",
    )

    assert result["ok"] is False
    assert result["denied"] is True
