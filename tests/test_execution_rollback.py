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


def test_patch_edit_is_rolled_back_when_later_step_fails(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _set_workspace(monkeypatch, tmp_path)
    target = workspace / "target.txt"
    target.write_text("old\n", encoding="utf-8")

    from agent_core.plan_executor import approve_plan, execute_plan, submit_plan
    from agent_core.plan_schema import Plan, ToolStep

    plan = Plan(
        plan_id="rollback-patch-edit-test",
        steps=(
            ToolStep(
                step_id=1,
                tool="PATCH_EDIT",
                capability="patch.edit",
                args={
                    "path": "target.txt",
                    "edits": [
                        {
                            "old_text": "old\n",
                            "new_text": "new\n",
                        }
                    ],
                },
            ),
            ToolStep(
                step_id=2,
                tool="TEST_RUN",
                capability="test.run",
                args={
                    "argv": ["python", "-c", "import sys; sys.exit(1)"],
                    "timeout_seconds": 10,
                },
            ),
        ),
    )

    plan_hash = submit_plan(plan)["plan_hash"]
    approve_plan(plan_hash)

    result = execute_plan(_make_gateway(), plan_hash)

    assert result["summary"]["execution_status"] == "TEST_FAILURE"
    assert target.read_text(encoding="utf-8") == "old\n"
    assert result["summary"]["rollback"]["attempted"] is True
    assert result["summary"]["rollback"]["restored_paths"] == ["target.txt"]
    assert result["summary"]["rollback"]["errors"] == []
    assert result["failure_envelope"]["rollback"]["restored_paths"] == ["target.txt"]


def test_file_create_is_rolled_back_when_later_step_fails(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _set_workspace(monkeypatch, tmp_path)
    target = workspace / "created.txt"

    from agent_core.plan_executor import approve_plan, execute_plan, submit_plan
    from agent_core.plan_schema import Plan, ToolStep

    plan = Plan(
        plan_id="rollback-file-create-test",
        steps=(
            ToolStep(
                step_id=1,
                tool="FILE_CREATE",
                capability="file.create",
                args={
                    "path": "created.txt",
                    "content": "created\n",
                },
            ),
            ToolStep(
                step_id=2,
                tool="TEST_RUN",
                capability="test.run",
                args={
                    "argv": ["python", "-c", "import sys; sys.exit(1)"],
                    "timeout_seconds": 10,
                },
            ),
        ),
    )

    plan_hash = submit_plan(plan)["plan_hash"]
    approve_plan(plan_hash)

    result = execute_plan(_make_gateway(), plan_hash)

    assert result["summary"]["execution_status"] == "TEST_FAILURE"
    assert not target.exists()
    assert result["summary"]["rollback"]["attempted"] is True
    assert result["summary"]["rollback"]["deleted_paths"] == ["created.txt"]
    assert result["summary"]["rollback"]["errors"] == []
    assert result["failure_envelope"]["rollback"]["deleted_paths"] == ["created.txt"]


def test_duplicate_patch_edits_restore_original_content_once(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _set_workspace(monkeypatch, tmp_path)
    target = workspace / "target.txt"
    target.write_text("alpha\n", encoding="utf-8")

    from agent_core.plan_executor import approve_plan, execute_plan, submit_plan
    from agent_core.plan_schema import Plan, ToolStep

    plan = Plan(
        plan_id="rollback-duplicate-patch-edit-test",
        steps=(
            ToolStep(
                step_id=1,
                tool="PATCH_EDIT",
                capability="patch.edit",
                args={
                    "path": "target.txt",
                    "edits": [
                        {
                            "old_text": "alpha\n",
                            "new_text": "beta\n",
                        }
                    ],
                },
            ),
            ToolStep(
                step_id=2,
                tool="PATCH_EDIT",
                capability="patch.edit",
                args={
                    "path": "target.txt",
                    "edits": [
                        {
                            "old_text": "beta\n",
                            "new_text": "gamma\n",
                        }
                    ],
                },
            ),
            ToolStep(
                step_id=3,
                tool="TEST_RUN",
                capability="test.run",
                args={
                    "argv": ["python", "-c", "import sys; sys.exit(1)"],
                    "timeout_seconds": 10,
                },
            ),
        ),
    )

    plan_hash = submit_plan(plan)["plan_hash"]
    approve_plan(plan_hash)

    result = execute_plan(_make_gateway(), plan_hash)

    assert result["summary"]["execution_status"] == "TEST_FAILURE"
    assert target.read_text(encoding="utf-8") == "alpha\n"
    assert result["summary"]["rollback"]["restored_paths"] == ["target.txt"]
    assert result["summary"]["rollback"]["errors"] == []
