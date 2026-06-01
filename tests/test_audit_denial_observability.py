from __future__ import annotations

from pathlib import Path

from tools import gateway as gateway_module
from tools.gateway import ToolGateway


class Denied:
    allowed = False
    reason = "token_denied"
    token_id = "token-1"


def test_test_run_invalid_cwd_denial_is_audited(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(gateway_module, "log_event", lambda event, meta=None: events.append((event, meta or {})))

    result = ToolGateway().test_run(
        argv=["python", "-m", "pytest", "-q"],
        cwd="outside",
    )

    assert result["ok"] is False
    assert result["denied"] is True
    assert any(event == "TEST_RUN_DENIED" for event, _ in events)


def test_patch_apply_token_denial_is_audited(monkeypatch, tmp_path) -> None:
    events = []
    monkeypatch.setattr(gateway_module, "validate_token", lambda **_: Denied())
    monkeypatch.setattr(gateway_module, "log_event", lambda event, meta=None: events.append((event, meta or {})))

    target = tmp_path / "x.txt"
    target.write_text("old", encoding="utf-8")

    try:
        ToolGateway().patch_apply(target, "new", cap_token_id="token-1")
    except PermissionError:
        pass

    assert any(event == "DENY_WRITE" and meta.get("decision") == "deny" for event, meta in events)


def test_patch_edit_token_denial_is_audited(monkeypatch, tmp_path) -> None:
    events = []
    monkeypatch.setattr(gateway_module, "validate_token", lambda **_: Denied())
    monkeypatch.setattr(gateway_module, "log_event", lambda event, meta=None: events.append((event, meta or {})))

    result = ToolGateway().patch_edit(
        tmp_path / "x.txt",
        edits=[{"old_text": "a", "new_text": "b"}],
        cap_token_id="token-1",
    )

    assert result["ok"] is False
    assert result["denied"] is True
    assert any(event == "PATCH_EDIT_DENIED" and meta.get("decision") == "deny" for event, meta in events)
