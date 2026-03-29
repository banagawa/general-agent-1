from __future__ import annotations

from pathlib import Path

import pytest

from policy.capabilities import issue_token
from tools.gateway import ToolGateway
from tools.fs_tools import FileSystemTools


def _set_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))
    return workspace


@pytest.fixture()
def workspace_gateway(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    workspace = _set_workspace(monkeypatch, tmp_path)
    gateway = ToolGateway()
    return workspace, gateway


def test_fs_create_fails_if_target_exists(tmp_path: Path):
    fs = FileSystemTools()
    path = tmp_path / "exists.txt"
    path.write_text("already here", encoding="utf-8")

    with pytest.raises(ValueError, match="file already exists"):
        fs.create_file(path, "new content")


def test_fs_create_fails_if_parent_missing(tmp_path: Path):
    fs = FileSystemTools()
    path = tmp_path / "missing_parent" / "new.txt"

    with pytest.raises(ValueError, match="parent directory does not exist"):
        fs.create_file(path, "hello")


def test_gateway_create_fails_if_target_exists(workspace_gateway):
    workspace, gateway = workspace_gateway

    path = workspace / "docs" / "exists.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("already here", encoding="utf-8")

    token = issue_token(
        actions=["FS_CREATE_FILE"],
        scope={"path": str(path.resolve())},
        constraints={"test_case": "exists_denied"},
        ttl_seconds=300,
    )

    with pytest.raises(ValueError, match="file already exists"):
        gateway.create_file(
            path=path,
            content="new content",
            cap_token_id=token.id,
        )


def test_gateway_create_fails_if_parent_missing(workspace_gateway):
    workspace, gateway = workspace_gateway

    path = workspace / "missing_parent" / "new.txt"

    token = issue_token(
        actions=["FS_CREATE_FILE"],
        scope={"path": str(path.resolve())},
        constraints={"test_case": "parent_missing"},
        ttl_seconds=300,
    )

    with pytest.raises(ValueError, match="parent directory does not exist"):
        gateway.create_file(
            path=path,
            content="hello",
            cap_token_id=token.id,
        )


