from __future__ import annotations

from pathlib import Path
import pytest


def _set_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))
    return workspace


@pytest.fixture()
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_validate_execution_request_rejects_uppercase_hash(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_workspace(monkeypatch, tmp_path)

    from agent_core.validators import validate_execution_request

    with pytest.raises(RuntimeError, match="plan hash must be lowercase"):
        validate_execution_request("A" * 64)


def test_validate_execution_request_rejects_wrong_length(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_workspace(monkeypatch, tmp_path)

    from agent_core.validators import validate_execution_request

    with pytest.raises(RuntimeError, match="invalid plan hash length"):
        validate_execution_request("a" * 63)


def test_validate_execution_request_rejects_non_hex(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_workspace(monkeypatch, tmp_path)

    from agent_core.validators import validate_execution_request

    with pytest.raises(RuntimeError, match="plan hash must be hex"):
        validate_execution_request("g" * 64)


def test_validate_execution_request_rejects_empty(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_workspace(monkeypatch, tmp_path)

    from agent_core.validators import validate_execution_request

    with pytest.raises(RuntimeError, match="plan hash empty"):
        validate_execution_request("")


def test_validate_approved_meta_rejects_unknown_field(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_workspace(monkeypatch, tmp_path)

    from agent_core.validators import validate_approved_meta

    meta = {
        "plan_hash": "a" * 64,
        "approved_at": "2026-03-20T00:00:00Z",
        "approval_source": "manual",
        "workspace_fingerprint": "b" * 64,
        "plan_id": "test-plan-1",
        "drift_check_enabled": True,
        "unexpected": "x",
    }

    with pytest.raises(RuntimeError, match="unknown approval metadata fields"):
        validate_approved_meta(meta)


def test_validate_approved_meta_rejects_missing_required_field(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_workspace(monkeypatch, tmp_path)

    from agent_core.validators import validate_approved_meta

    meta = {
        "plan_hash": "a" * 64,
        "approved_at": "2026-03-20T00:00:00Z",
        "approval_source": "manual",
        "workspace_fingerprint": "b" * 64,
        # missing plan_id
        "drift_check_enabled": True,
    }

    with pytest.raises(RuntimeError, match="missing required approval metadata field: plan_id"):
        validate_approved_meta(meta)


def test_validate_approved_meta_rejects_bad_drift_flag_type(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_workspace(monkeypatch, tmp_path)

    from agent_core.validators import validate_approved_meta

    meta = {
        "plan_hash": "a" * 64,
        "approved_at": "2026-03-20T00:00:00Z",
        "approval_source": "manual",
        "workspace_fingerprint": "b" * 64,
        "plan_id": "test-plan-1",
        "drift_check_enabled": "true",
    }

    with pytest.raises(RuntimeError, match="drift_check_enabled must be bool"):
        validate_approved_meta(meta)
