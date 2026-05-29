from __future__ import annotations

from pathlib import Path

from policy.cmd_policy import validate_test_run_argv
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


def test_test_run_policy_allows_existing_version_probe() -> None:
    decision = validate_test_run_argv(["python", "--version"])

    assert decision.allowed is True


def test_test_run_policy_allows_existing_failure_probe() -> None:
    decision = validate_test_run_argv(["python", "-c", "import sys; sys.exit(1)"])

    assert decision.allowed is True


def test_test_run_policy_allows_pytest_forms() -> None:
    assert validate_test_run_argv(["python", "-m", "pytest", "tests"]).allowed is True
    assert validate_test_run_argv(["python3", "-m", "pytest", "tests"]).allowed is True
    assert validate_test_run_argv(["py", "-m", "pytest", "tests"]).allowed is True
    assert validate_test_run_argv(["pytest", "tests"]).allowed is True


def test_test_run_policy_allows_common_pytest_args() -> None:
    decision = validate_test_run_argv([
        "python",
        "-m",
        "pytest",
        "-q",
        "-k",
        "test_name",
        "tests/test_example.py::test_case",
        "--maxfail=1",
    ])

    assert decision.allowed is True


def test_test_run_policy_denies_inline_file_write() -> None:
    decision = validate_test_run_argv([
        "python",
        "-c",
        "open('owned.txt','w').write('x')",
    ])

    assert decision.allowed is False
    assert decision.reason == "test_run_inline_python_not_allowlisted"


def test_test_run_policy_denies_arbitrary_script() -> None:
    decision = validate_test_run_argv(["python", "scripts/run_tests.py"])

    assert decision.allowed is False
    assert decision.reason == "test_run_python_shape_not_allowlisted"


def test_test_run_policy_denies_other_python_module() -> None:
    decision = validate_test_run_argv(["python", "-m", "pip", "install", "pytest"])

    assert decision.allowed is False
    assert decision.reason == "test_run_python_shape_not_allowlisted"


def test_test_run_policy_denies_parent_traversal_target() -> None:
    decision = validate_test_run_argv(["python", "-m", "pytest", "../tests"])

    assert decision.allowed is False
    assert decision.reason == "unsafe_pytest_arg"


def test_test_run_policy_denies_rootdir_rebinding() -> None:
    decision = validate_test_run_argv([
        "python",
        "-m",
        "pytest",
        "--rootdir=/tmp/outside",
    ])

    assert decision.allowed is False
    assert decision.reason == "unsafe_pytest_arg"


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
        argv=["python", "--version"],
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
        argv=["python", "-c", "import sys; sys.exit(1)"],
        timeout_seconds=10,
        cwd="app",
    )

    assert result["ok"] is True
    assert calls["workspace_root"] == Path("APP")


def test_test_run_denies_inline_file_write_before_execution(monkeypatch) -> None:
    calls = {"ran": False}

    monkeypatch.setattr(gateway_module, "validate_token", lambda **_: Allowed())
    monkeypatch.setattr(gateway_module, "get_workspace_root", lambda: Path("WORKSPACE"))
    monkeypatch.setattr(gateway_module, "get_app_root", lambda: Path("APP"))

    def fake_run_cmd(*, argv, workspace_root, timeout):
        calls["ran"] = True
        return _fake_run_result()

    monkeypatch.setattr(gateway_module, "run_cmd", fake_run_cmd)

    result = ToolGateway().test_run(
        argv=["python", "-c", "open('owned.txt','w').write('x')"],
        timeout_seconds=10,
        cwd="app",
    )

    assert result["ok"] is False
    assert result["denied"] is True
    assert result["reason"] == "test_run_inline_python_not_allowlisted"
    assert calls["ran"] is False
