from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import pytest

from policy.capabilities import issue_token


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


def _read_audit_events(cwd: Path) -> list[dict]:
    audit_file = cwd / ".audit" / "audit.jsonl"
    assert audit_file.exists(), "audit file missing"
    lines = audit_file.read_text(encoding="utf-8").splitlines()
    assert lines, "audit file empty"
    return [json.loads(line) for line in lines]


def _last_event(cwd: Path, event_name: str) -> dict:
    events = _read_audit_events(cwd)
    for e in reversed(events):
        if e.get("event") == event_name:
            return e
    raise AssertionError(f"missing audit event: {event_name}")


def test_gateway_patch_edit_executes_exact_single_match(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = _set_workspace(monkeypatch, tmp_path)
    p = (workspace / "sample.txt").resolve()
    p.write_text("hello old world\n", encoding="utf-8")

    gw = _make_gateway()

    tok = issue_token(
        actions=["FS_EDIT_PATCH"],
        scope={"path": str(p)},
        ttl_seconds=60,
    )

    res = gw.patch_edit(
        path=p,
        edits=[{"old_text": "old", "new_text": "new"}],
        cap_token_id=tok.id,
    )

    assert res["ok"] is True
    assert res["changed"] is True
    assert p.read_text(encoding="utf-8") == "hello new world\n"

    e = _last_event(isolated_repo, "PATCH_EDIT_EXECUTED")
    meta = e.get("meta") or {}
    assert meta.get("path") == str(p)
    assert meta.get("decision") == "allow"


def test_gateway_patch_edit_denies_when_old_text_missing(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = _set_workspace(monkeypatch, tmp_path)
    p = (workspace / "sample.txt").resolve()
    p.write_text("hello world\n", encoding="utf-8")

    gw = _make_gateway()

    tok = issue_token(
        actions=["FS_EDIT_PATCH"],
        scope={"path": str(p)},
        ttl_seconds=60,
    )

    res = gw.patch_edit(
        path=p,
        edits=[{"old_text": "old", "new_text": "new"}],
        cap_token_id=tok.id,
    )

    assert res["ok"] is False
    assert res["denied"] is True
    assert res["reason"] == "PATCH_EDIT_OLD_TEXT_NOT_FOUND_AT_1"
    assert p.read_text(encoding="utf-8") == "hello world\n"


def test_gateway_patch_edit_denies_on_ambiguous_match_without_occurrence(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = _set_workspace(monkeypatch, tmp_path)
    p = (workspace / "sample.txt").resolve()
    p.write_text("x old y old z\n", encoding="utf-8")

    gw = _make_gateway()

    tok = issue_token(
        actions=["FS_EDIT_PATCH"],
        scope={"path": str(p)},
        ttl_seconds=60,
    )

    res = gw.patch_edit(
        path=p,
        edits=[{"old_text": "old", "new_text": "new"}],
        cap_token_id=tok.id,
    )

    assert res["ok"] is False
    assert res["denied"] is True
    assert res["reason"] == "PATCH_EDIT_AMBIGUOUS_MATCH_AT_1"
    assert p.read_text(encoding="utf-8") == "x old y old z\n"


def test_gateway_patch_edit_uses_occurrence_for_repeated_match(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = _set_workspace(monkeypatch, tmp_path)
    p = (workspace / "sample.txt").resolve()
    p.write_text("x old y old z\n", encoding="utf-8")

    gw = _make_gateway()

    tok = issue_token(
        actions=["FS_EDIT_PATCH"],
        scope={"path": str(p)},
        ttl_seconds=60,
    )

    res = gw.patch_edit(
        path=p,
        edits=[{"old_text": "old", "new_text": "new", "occurrence": 2}],
        cap_token_id=tok.id,
    )

    assert res["ok"] is True
    assert res["changed"] is True
    assert p.read_text(encoding="utf-8") == "x old y new z\n"


def test_gateway_patch_edit_denies_hash_mismatch(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = _set_workspace(monkeypatch, tmp_path)
    p = (workspace / "sample.txt").resolve()
    p.write_text("old\n", encoding="utf-8")

    gw = _make_gateway()

    tok = issue_token(
        actions=["FS_EDIT_PATCH"],
        scope={"path": str(p)},
        ttl_seconds=60,
    )

    wrong_hash = sha256("different\n".encode("utf-8")).hexdigest()

    res = gw.patch_edit(
        path=p,
        edits=[{"old_text": "old", "new_text": "new"}],
        expected_file_sha256_before=wrong_hash,
        cap_token_id=tok.id,
    )

    assert res["ok"] is False
    assert res["denied"] is True
    assert res["reason"] == "PATCH_EDIT_HASH_MISMATCH"
    assert p.read_text(encoding="utf-8") == "old\n"


def test_gateway_patch_edit_is_atomic_across_multiple_edits(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = _set_workspace(monkeypatch, tmp_path)
    p = (workspace / "sample.txt").resolve()
    p.write_text("a old b keep c\n", encoding="utf-8")

    gw = _make_gateway()

    tok = issue_token(
        actions=["FS_EDIT_PATCH"],
        scope={"path": str(p)},
        ttl_seconds=60,
    )

    res = gw.patch_edit(
        path=p,
        edits=[
            {"old_text": "old", "new_text": "new"},
            {"old_text": "missing", "new_text": "x"},
        ],
        cap_token_id=tok.id,
    )

    assert res["ok"] is False
    assert res["denied"] is True
    assert res["reason"] == "PATCH_EDIT_OLD_TEXT_NOT_FOUND_AT_2"
    assert p.read_text(encoding="utf-8") == "a old b keep c\n"

def test_patch_edit_noop_edit_is_safe(tmp_path, monkeypatch):
    from tools.gateway import ToolGateway
    from policy.capabilities import issue_token

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))

    p = workspace / "sample.txt"
    p.write_text("same\n", encoding="utf-8")

    gw = ToolGateway()

    tok = issue_token(
        actions=["FS_EDIT_PATCH"],
        scope={"path": str(p)},
        ttl_seconds=60,
    )

    res = gw.patch_edit(
        path=p,
        edits=[{"old_text": "same", "new_text": "same"}],
        cap_token_id=tok.id,
    )

    assert res["ok"] is True
    assert res["changed"] is False
