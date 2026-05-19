from __future__ import annotations

from pathlib import Path
import time

import pytest

from policy.capabilities import issue_token, revoke_token, validate_token


@pytest.fixture()
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_missing_token_denies(isolated_repo: Path):
    vr = validate_token(None, action="FS_WRITE_PATCH", context={"path": "/x"})
    assert vr.allowed is False
    assert vr.reason == "MISSING_TOKEN"


def test_expired_token_denies(isolated_repo: Path):
    tok = issue_token(actions=["FS_WRITE_PATCH"], scope={"path": "/x"}, ttl_seconds=1)
    time.sleep(1.2)
    vr = validate_token(tok.id, action="FS_WRITE_PATCH", context={"path": "/x"})
    assert vr.allowed is False
    assert vr.reason == "EXPIRED_TOKEN"


def test_revoked_token_denies(isolated_repo: Path):
    tok = issue_token(actions=["FS_WRITE_PATCH"], scope={"path": "/x"}, ttl_seconds=60)
    revoke_token(tok.id)
    vr = validate_token(tok.id, action="FS_WRITE_PATCH", context={"path": "/x"})
    assert vr.allowed is False
    assert vr.reason == "REVOKED_TOKEN"


def test_wrong_action_denies(isolated_repo: Path):
    tok = issue_token(actions=["CMD_RUN"], scope={}, ttl_seconds=60)
    vr = validate_token(tok.id, action="FS_WRITE_PATCH", context={"path": "/x"})
    assert vr.allowed is False
    assert vr.reason == "ACTION_NOT_ALLOWED"


def test_scope_mismatch_denies(isolated_repo: Path):
    tok = issue_token(actions=["FS_WRITE_PATCH"], scope={"path": "/allowed"}, ttl_seconds=60)
    vr = validate_token(tok.id, action="FS_WRITE_PATCH", context={"path": "/other"})
    assert vr.allowed is False
    assert vr.reason == "INSUFFICIENT_SCOPE"


def test_allow_path_scoped_token(isolated_repo: Path):
    tok = issue_token(actions=["FS_WRITE_PATCH"], scope={"path": "/x"}, ttl_seconds=60)
    vr = validate_token(tok.id, action="FS_WRITE_PATCH", context={"path": "/x"})
    assert vr.allowed is True
    assert vr.reason is None

def test_allow_path_scoped_edit_token(isolated_repo: Path):
    tok = issue_token(actions=["FS_EDIT_PATCH"], scope={"path": "/x"}, ttl_seconds=60)
    vr = validate_token(tok.id, action="FS_EDIT_PATCH", context={"path": "/x"})
    assert vr.allowed is True
    assert vr.reason is None
