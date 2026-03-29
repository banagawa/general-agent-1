from __future__ import annotations

import os
from pathlib import Path

import pytest

from policy.capabilities import issue_token
from tools.gateway import ToolGateway


def _set_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))

    return workspace


@pytest.fixture()
def gateway_with_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    workspace = _set_workspace(monkeypatch, tmp_path)
    gateway = ToolGateway()
    return gateway, workspace


def test_file_create_denied_without_token(gateway_with_workspace):
    gateway, workspace = gateway_with_workspace

    path = workspace / "docs" / "no_token.txt"
    path.parent.mkdir(parents=True, exist_ok=True)

    with pytest.raises(PermissionError):
        gateway.create_file(
            path=path,
            content="hello",
            cap_token_id=None,
        )


def test_file_create_denied_wrong_scope(gateway_with_workspace):
    gateway, workspace = gateway_with_workspace

    target = workspace / "docs" / "target.txt"
    target.parent.mkdir(parents=True, exist_ok=True)

    wrong_scope_token = issue_token(
        actions=["FS_CREATE_FILE"],
        scope={"path": str(workspace / "docs" / "other.txt")},
        constraints={"test_case": "wrong_scope"},
        ttl_seconds=300,
    )

    with pytest.raises(PermissionError):
        gateway.create_file(
            path=target,
            content="hello",
            cap_token_id=wrong_scope_token.id,
        )


def test_file_create_denied_outside_workspace(gateway_with_workspace, tmp_path: Path):
    gateway, workspace = gateway_with_workspace

    outside = tmp_path / "outside"
    outside.mkdir(parents=True, exist_ok=True)

    outside_path = outside / "outside.txt"

    token = issue_token(
        actions=["FS_CREATE_FILE"],
        scope={"path": str(outside_path.resolve())},
        constraints={"test_case": "outside"},
        ttl_seconds=300,
    )

    with pytest.raises(PermissionError):
        gateway.create_file(
            path=outside_path,
            content="hello",
            cap_token_id=token.id,
        )


def test_file_create_success(gateway_with_workspace):
    gateway, workspace = gateway_with_workspace

    path = workspace / "docs" / "ok.txt"
    path.parent.mkdir(parents=True, exist_ok=True)

    token = issue_token(
        actions=["FS_CREATE_FILE"],
        scope={"path": str(path.resolve())},
        constraints={"test_case": "success"},
        ttl_seconds=300,
    )

    result = gateway.create_file(
        path=path,
        content="hello from gateway",
        cap_token_id=token.id,
    )

    assert path.exists()
    assert path.read_text(encoding="utf-8") == "hello from gateway"
    assert str(path) == result
