from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.plan_executor import validate_plan_approval_gate
from agent_core.plan_schema import Plan, ToolStep


def _plan(tool: str, path: str) -> Plan:
    capability_by_tool = {
        "PATCH_APPLY": "patch.apply",
        "PATCH_EDIT": "patch.edit",
        "FILE_CREATE": "file.create",
    }
    args = {"path": path}
    if tool == "PATCH_APPLY":
        args["new_content"] = "replacement"
    elif tool == "PATCH_EDIT":
        args["edits"] = [{"old_text": "old", "new_text": "new"}]
    elif tool == "FILE_CREATE":
        args["content"] = "new file"

    return Plan(
        plan_id="approval-gate-test",
        steps=(
            ToolStep(
                step_id=1,
                tool=tool,
                capability=capability_by_tool[tool],
                args=args,
            ),
        ),
    )


def test_approval_gate_allows_patch_apply_existing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path))
    target = tmp_path / "existing.py"
    target.write_text("old", encoding="utf-8")

    validate_plan_approval_gate(_plan("PATCH_APPLY", "existing.py"))


def test_approval_gate_rejects_patch_apply_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path))

    with pytest.raises(ValueError, match="PATCH_APPLY target does not exist"):
        validate_plan_approval_gate(_plan("PATCH_APPLY", "missing.py"))


def test_approval_gate_rejects_patch_edit_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path))

    with pytest.raises(ValueError, match="PATCH_EDIT target does not exist"):
        validate_plan_approval_gate(_plan("PATCH_EDIT", "missing.py"))


def test_approval_gate_allows_file_create_missing_file_with_existing_parent(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path))
    (tmp_path / "tests").mkdir()

    validate_plan_approval_gate(_plan("FILE_CREATE", "tests/new_test.py"))


def test_approval_gate_rejects_file_create_existing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path))
    target = tmp_path / "already_exists.py"
    target.write_text("old", encoding="utf-8")

    with pytest.raises(ValueError, match="FILE_CREATE target already exists"):
        validate_plan_approval_gate(_plan("FILE_CREATE", "already_exists.py"))


def test_approval_gate_rejects_parent_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path))

    with pytest.raises(ValueError, match="parent traversal"):
        validate_plan_approval_gate(_plan("FILE_CREATE", "../outside.py"))
