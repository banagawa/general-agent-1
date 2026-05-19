from pathlib import Path
import pytest

from policy.capabilities import issue_token


def _set_workspace(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))
    return workspace


def _make_gateway():
    from tools.gateway import ToolGateway
    return ToolGateway()


def test_patch_edit_cannot_escape_workspace(tmp_path, monkeypatch):
    workspace = _set_workspace(monkeypatch, tmp_path)

    outside = tmp_path / "outside.txt"
    outside.write_text("old", encoding="utf-8")

    gw = _make_gateway()

    tok = issue_token(
        actions=["FS_EDIT_PATCH"],
        scope={"path": str(outside)},
        ttl_seconds=60,
    )

    res = gw.patch_edit(
        path=outside,
        edits=[{"old_text": "old", "new_text": "new"}],
        cap_token_id=tok.id,
    )

    assert res["ok"] is False
    assert res["denied"] is True
