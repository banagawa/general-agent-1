from __future__ import annotations

from pathlib import Path
import pytest


def _set_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))
    return workspace


def _make_gateway():
    from tools.gateway import ToolGateway
    return ToolGateway()


@pytest.fixture()
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_execute_plan_patch_edit_success_path(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = _set_workspace(monkeypatch, tmp_path)
    (workspace / "sample.txt").write_text("old\n", encoding="utf-8")

    from agent_core.plan_executor import approve_plan, execute_plan, submit_plan
    from agent_core.plan_schema import Plan, ToolStep

    gw = _make_gateway()

    plan = Plan(
        plan_id="patch-edit-success-1",
        steps=(
            ToolStep(
                step_id=1,
                tool="PATCH_EDIT",
                capability="patch.edit",
                args={
                    "path": "sample.txt",
                    "edits": [
                        {
                            "old_text": "old",
                            "new_text": "new",
                        }
                    ],
                },
            ),
        ),
        metadata={},
    )

    submit_result = submit_plan(plan)
    plan_hash = submit_result["plan_hash"]
    approve_plan(plan_hash)

    payload = execute_plan(gw, plan_hash)

    assert payload["summary"]["execution_status"] == "SUCCESS"
    assert payload["summary"]["changed_paths"] == ["sample.txt"]
    assert (workspace / "sample.txt").read_text(encoding="utf-8") == "new\n"


def test_execute_plan_patch_edit_rejected_path(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = _set_workspace(monkeypatch, tmp_path)
    (workspace / "sample.txt").write_text("old\n", encoding="utf-8")

    from agent_core.plan_executor import approve_plan, execute_plan, submit_plan
    from agent_core.plan_schema import Plan, ToolStep

    gw = _make_gateway()

    plan = Plan(
        plan_id="patch-edit-rejected-1",
        steps=(
            ToolStep(
                step_id=1,
                tool="PATCH_EDIT",
                capability="patch.edit",
                args={
                    "path": "sample.txt",
                    "edits": [
                        {
                            "old_text": "missing",
                            "new_text": "new",
                        }
                    ],
                },
            ),
        ),
        metadata={},
    )

    submit_result = submit_plan(plan)
    plan_hash = submit_result["plan_hash"]
    approve_plan(plan_hash)

    payload = execute_plan(gw, plan_hash)

    assert payload["summary"]["execution_status"] == "PATCH_REJECTED"
    assert payload["summary"]["changed_paths"] == []

    envelope = payload["failure_envelope"]
    assert envelope["failure_class"] == "PATCH_REJECTED"
    assert envelope["tool"] == "PATCH_EDIT"
