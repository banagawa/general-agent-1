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


def test_summary_records_patch_edit_paths_on_success(
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
        plan_id="summary-patch-edit-success-1",
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

    summary = payload["summary"]
    assert summary["execution_status"] == "SUCCESS"
    assert summary["modified_paths"] == ["sample.txt"]
    assert summary["patch_edit_paths"] == ["sample.txt"]
    assert summary["patch_apply_paths"] == []
    assert summary["changed_paths"] == ["sample.txt"]


def test_summary_records_patch_apply_paths_on_success(
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
        plan_id="summary-patch-apply-success-1",
        steps=(
            ToolStep(
                step_id=1,
                tool="PATCH_APPLY",
                capability="patch.apply",
                args={
                    "path": "sample.txt",
                    "new_content": "new\n",
                },
            ),
        ),
        metadata={},
    )

    submit_result = submit_plan(plan)
    plan_hash = submit_result["plan_hash"]
    approve_plan(plan_hash)

    payload = execute_plan(gw, plan_hash)

    summary = payload["summary"]
    assert summary["execution_status"] == "SUCCESS"
    assert summary["modified_paths"] == ["sample.txt"]
    assert summary["patch_apply_paths"] == ["sample.txt"]
    assert summary["patch_edit_paths"] == []
    assert summary["changed_paths"] == ["sample.txt"]


def test_failure_envelope_keeps_path_buckets_for_patch_edit_rejection(
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
        plan_id="summary-patch-edit-failure-1",
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

    summary = payload["summary"]
    envelope = payload["failure_envelope"]

    assert summary["execution_status"] == "PATCH_REJECTED"
    assert summary["modified_paths"] == []
    assert summary["patch_edit_paths"] == []
    assert summary["patch_apply_paths"] == []
    assert summary["changed_paths"] == []

    assert envelope["failure_class"] == "PATCH_REJECTED"
    assert envelope["modified_paths"] == []
    assert envelope["patch_edit_paths"] == []
    assert envelope["patch_apply_paths"] == []
    assert envelope["changed_paths"] == []
