from __future__ import annotations

from pathlib import Path
import pytest


def _set_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))
    return workspace

def _workspace_files(workspace: Path) -> list[str]:
    out: list[str] = []
    for path in sorted(workspace.rglob("*")):
        if path.is_file():
            out.append(path.relative_to(workspace).as_posix())
    return out

def _make_gateway():
    from tools.gateway import ToolGateway
    return ToolGateway()


@pytest.fixture()
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_second_execution_of_same_plan_is_denied(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = _set_workspace(monkeypatch, tmp_path)

    from agent_core.plan_schema import Plan, ToolStep
    from agent_core.plan_executor import submit_plan, approve_plan, execute_plan
    from agent_core.plan_store import load_approved_plan_meta
    from agent_core.workspace_fingerprint import compute_workspace_fingerprint

    gw = _make_gateway()

    plan = Plan(
        plan_id="replay-test-1",
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

    submit_result = submit_plan(plan)
    plan_hash = submit_result["plan_hash"]

    approve_result = approve_plan(plan_hash)
    assert approve_result["status"] == "APPROVED"

    meta = load_approved_plan_meta(plan_hash)
    current = compute_workspace_fingerprint()

    assert current == meta["workspace_fingerprint"], {
        "approved": meta["workspace_fingerprint"],
        "current": current,
        "files": _workspace_files(workspace),
    }

    first_result = execute_plan(gw, plan_hash)
    assert isinstance(first_result, dict)
    assert first_result["plan_hash"] == plan_hash

    with pytest.raises(RuntimeError, match="approved plan already executed"):
        execute_plan(gw, plan_hash)
