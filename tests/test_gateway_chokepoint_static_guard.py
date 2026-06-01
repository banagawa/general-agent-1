from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _py_files_under(dirname: str) -> list[Path]:
    return sorted((ROOT / dirname).rglob("*.py"))


def test_agent_core_does_not_import_filesystem_tool_directly() -> None:
    offenders = []
    for path in _py_files_under("agent_core"):
        text = path.read_text(encoding="utf-8")
        if "tools.fs_tools" in text or "FileSystemTools" in text:
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []


def test_execute_step_only_dispatches_through_gateway_methods() -> None:
    text = (ROOT / "agent_core" / "execute_step.py").read_text(encoding="utf-8")

    forbidden = [
        "FileSystemTools",
        "run_cmd(",
        "PolicyEngine(",
        ".write_text(",
        ".unlink(",
        "open(",
    ]
    hits = [token for token in forbidden if token in text]

    assert hits == []
    assert "gateway.patch_apply(" in text
    assert "gateway.patch_edit(" in text
    assert "gateway.create_file(" in text
    assert "gateway.test_run(" in text
    assert "gateway.git_run(" in text
