from __future__ import annotations

from pathlib import Path


def test_plan_artifact_ownership_document_exists():
    doc = Path("docs/plan_artifact_ownership.md")
    assert doc.is_file()

    text = doc.read_text(encoding="utf-8")

    assert "plans/pending/" in text
    assert "plans/approved/" in text
    assert "plans/executed/" in text
    assert "plans/failures/" in text
    assert "plans/summaries/" in text


def test_plan_artifacts_are_characterized_as_runtime_history():
    text = Path("docs/plan_artifact_ownership.md").read_text(encoding="utf-8")

    assert "Runtime history" in text
    assert "Runtime workflow state" in text
    assert "not target project source files" in text


def test_future_runtime_history_operations_are_documented_but_not_implemented():
    text = Path("docs/plan_artifact_ownership.md").read_text(encoding="utf-8")

    assert "runtime migration tool" in text
    assert "runtime export tool" in text
    assert "disk usage health monitoring" in text
    assert "No cleanup, deletion, compaction, or retention enforcement" in text
