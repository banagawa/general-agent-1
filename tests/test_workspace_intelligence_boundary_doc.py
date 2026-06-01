from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_workspace_intelligence_boundary_doc_exists() -> None:
    doc = ROOT / "docs" / "anchors" / "workspace-intelligence-boundary.md"
    text = doc.read_text(encoding="utf-8")

    assert "must not grant authority" in text
    assert "ToolGateway + PolicyEngine remain the authority boundary" in text
    assert "ArtifactID resolution fails closed" in text
