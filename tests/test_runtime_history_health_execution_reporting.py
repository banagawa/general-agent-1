from __future__ import annotations

from agent_core.plan_executor import approve_plan, execute_plan, submit_plan
from agent_core.plan_schema import Plan, ToolStep
from tools.gateway import ToolGateway


def _set_workspace(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace_container = app_root / "workspace"
    workspace = workspace_container / "project-a"
    app_root.mkdir()
    workspace_container.mkdir()
    workspace.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    return workspace


def test_success_summary_includes_runtime_history_health_without_affecting_success(tmp_path, monkeypatch):
    _set_workspace(tmp_path, monkeypatch)

    plan = Plan(
        plan_id="runtime-health-summary-success",
        steps=(
            ToolStep(
                step_id=1,
                tool="TEST_RUN",
                capability="test.run",
                args={
                    "argv": ["python", "--version"],
                    "timeout_seconds": 10,
                },
            ),
        ),
        metadata={},
    )

    submitted = submit_plan(plan)
    approve_plan(submitted["plan_hash"])
    result = execute_plan(ToolGateway(), submitted["plan_hash"])

    summary = result["summary"]
    health = summary["runtime_history_health"]

    assert summary["execution_status"] == "SUCCESS"
    assert health["total_bytes"] >= 0
    assert health["file_count"] >= 0
    assert isinstance(health["warnings"], list)


def test_failure_envelope_includes_runtime_history_health_without_changing_failure_class(tmp_path, monkeypatch):
    _set_workspace(tmp_path, monkeypatch)

    plan = Plan(
        plan_id="runtime-health-summary-failure",
        steps=(
            ToolStep(
                step_id=1,
                tool="TEST_RUN",
                capability="test.run",
                args={
                    "argv": ["python", "-c", "import sys; sys.exit(1)"],
                    "timeout_seconds": 10,
                },
            ),
        ),
        metadata={},
    )

    submitted = submit_plan(plan)
    approve_plan(submitted["plan_hash"])
    result = execute_plan(ToolGateway(), submitted["plan_hash"])

    summary = result["summary"]
    envelope = result["failure_envelope"]

    assert summary["execution_status"] == "TEST_FAILURE"
    assert envelope["failure_class"] == "TEST_FAILURE"
    assert "runtime_history_health" in summary
    assert "runtime_history_health" in envelope
    assert isinstance(summary["runtime_history_health"]["warnings"], list)


def test_runtime_health_collection_error_is_reported_not_raised(monkeypatch):
    import agent_core.plan_executor as plan_executor

    def boom():
        raise RuntimeError("health unavailable")

    monkeypatch.setattr(
        "agent_core.runtime_history_health.get_runtime_history_health",
        boom,
    )

    payload = plan_executor._runtime_history_health_summary()

    assert payload["available"] is False
    assert payload["error"] == "health unavailable"
    assert payload["warnings"] == []
