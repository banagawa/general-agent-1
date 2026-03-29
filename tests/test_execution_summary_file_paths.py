from __future__ import annotations

from agent_core.plan_executor import (
    _build_failure_envelope,
    _build_summary,
)


class DummyPlan:
    def __init__(self):
        self.metadata = {}


def test_build_summary_separates_created_and_modified_paths():
    plan = DummyPlan()
    results = [
        {
            "step_id": 1,
            "tool": "FILE_CREATE",
            "path": "docs/new_file.txt",
            "result": "docs/new_file.txt",
        },
        {
            "step_id": 2,
            "tool": "PATCH_APPLY",
            "path": "docs/existing_file.txt",
            "result": "--- original\n+++ modified\n@@\n-old\n+new\n",
        },
        {
            "step_id": 3,
            "tool": "PATCH_APPLY",
            "path": "docs/new_file.txt",
            "result": "--- original\n+++ modified\n@@\n-old\n+new\n",
        },
    ]

    summary = _build_summary(
        plan=plan,
        plan_hash="a" * 64,
        tx_id="tx_001",
        results=results,
        status="SUCCESS",
        started_at="2026-03-28T12:00:00Z",
        finished_at="2026-03-28T12:01:00Z",
    )

    assert summary["created_paths"] == ["docs/new_file.txt"]
    assert summary["modified_paths"] == ["docs/existing_file.txt", "docs/new_file.txt"]
    assert summary["changed_paths"] == ["docs/new_file.txt", "docs/existing_file.txt"]


def test_build_failure_envelope_separates_created_and_modified_paths():
    plan = DummyPlan()
    results = [
        {
            "step_id": 1,
            "tool": "FILE_CREATE",
            "path": "docs/new_file.txt",
            "result": "docs/new_file.txt",
        },
        {
            "step_id": 2,
            "tool": "PATCH_APPLY",
            "path": "docs/existing_file.txt",
            "result": "--- original\n+++ modified\n@@\n-old\n+new\n",
        },
    ]

    envelope = _build_failure_envelope(
        plan=plan,
        plan_hash="b" * 64,
        tx_id="tx_002",
        results=results,
        failure_class="FAILED",
        error=RuntimeError("boom"),
    )

    assert envelope["created_paths"] == ["docs/new_file.txt"]
    assert envelope["modified_paths"] == ["docs/existing_file.txt"]
    assert envelope["changed_paths"] == ["docs/new_file.txt", "docs/existing_file.txt"]
    assert envelope["requires_new_approval"] is True
