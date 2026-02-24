from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set


AUDIT_DIR = Path(".audit")
TOKENS_FILE = AUDIT_DIR / "capability_tokens.json"
REVOCATIONS_FILE = AUDIT_DIR / "capability_revocations.json"

# Deny reasons (MUST match Sprint A.5)
MISSING_TOKEN = "MISSING_TOKEN"
EXPIRED_TOKEN = "EXPIRED_TOKEN"
REVOKED_TOKEN = "REVOKED_TOKEN"
INSUFFICIENT_SCOPE = "INSUFFICIENT_SCOPE"
ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"


@dataclass(frozen=True)
class CapabilityToken:
    id: str
    actions: Set[str]
    scope: Dict[str, Any]
    constraints: Dict[str, Any]
    issued_at: datetime
    expires_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "actions": sorted(self.actions),
            "scope": self.scope,
            "constraints": self.constraints,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CapabilityToken":
        return CapabilityToken(
            id=str(data["id"]),
            actions=set(data.get("actions", [])),
            scope=dict(data.get("scope", {})),
            constraints=dict(data.get("constraints", {})),
            issued_at=_parse_dt(data.get("issued_at")),
            expires_at=_parse_dt(data.get("expires_at")),
        )


@dataclass(frozen=True)
class ValidationResult:
    allowed: bool
    reason: Optional[str] = None
    token_id: Optional[str] = None


def _parse_dt(v: Any) -> datetime:
    if not v:
        # Fail closed: missing timestamps are effectively expired
        return datetime.fromtimestamp(0, tz=timezone.utc)
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc)
    return datetime.fromisoformat(str(v)).astimezone(timezone.utc)


def _load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # Fail closed: corruption means "no usable tokens"
        return default


def _save_json(path: Path, obj: Any) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_tokens() -> Dict[str, Dict[str, Any]]:
    # token_id -> token_dict
    return _load_json(TOKENS_FILE, default={})


def _save_tokens(tokens: Dict[str, Dict[str, Any]]) -> None:
    _save_json(TOKENS_FILE, tokens)


def _load_revocations() -> Set[str]:
    data = _load_json(REVOCATIONS_FILE, default={"revoked": []})
    revoked = data.get("revoked", [])
    return set(map(str, revoked))


def _save_revocations(revoked: Set[str]) -> None:
    _save_json(REVOCATIONS_FILE, {"revoked": sorted(revoked)})


def issue_token(
    actions: Iterable[str],
    scope: Optional[Dict[str, Any]] = None,
    constraints: Optional[Dict[str, Any]] = None,
    ttl_seconds: int = 300,
) -> CapabilityToken:
    now = datetime.now(timezone.utc)
    token = CapabilityToken(
        id=str(uuid.uuid4()),
        actions=set(actions),
        scope=scope or {},
        constraints=constraints or {},
        issued_at=now,
        expires_at=now + timedelta(seconds=int(ttl_seconds)),
    )

    tokens = _load_tokens()
    tokens[token.id] = token.to_dict()
    _save_tokens(tokens)
    return token


def revoke_token(token_id: str) -> None:
    revoked = _load_revocations()
    revoked.add(str(token_id))
    _save_revocations(revoked)

    # Optional but helpful: remove from active token store
    tokens = _load_tokens()
    if str(token_id) in tokens:
        tokens.pop(str(token_id), None)
        _save_tokens(tokens)


def revoke_all_tokens() -> None:
    """
    "Big red button" replacement for global write-revocation.
    Leaves a persistent revocation set emptying actives.
    """
    _save_tokens({})
    # We do NOT need to mark all historical ids revoked; actives are cleared.
    # If an unknown token_id is presented, validation will fail closed.


def validate_token(
    token_id: Optional[str],
    action: str,
    context: Optional[Dict[str, Any]] = None,
) -> ValidationResult:
    """
    Fail closed:
    - Missing token => MISSING_TOKEN
    - Unknown/invalid token => REVOKED_TOKEN (no INVALID reason exists in spec)
    - Expired => EXPIRED_TOKEN
    - Revoked => REVOKED_TOKEN
    - Wrong action => ACTION_NOT_ALLOWED
    - Scope mismatch => INSUFFICIENT_SCOPE
    """
    ctx = context or {}

    if not token_id:
        return ValidationResult(False, MISSING_TOKEN, None)

    token_id = str(token_id)

    revoked = _load_revocations()
    if token_id in revoked:
        return ValidationResult(False, REVOKED_TOKEN, token_id)

    tokens = _load_tokens()
    raw = tokens.get(token_id)
    if not raw:
        # Fail closed: no INVALID_TOKEN reason in spec
        return ValidationResult(False, REVOKED_TOKEN, token_id)

    token = CapabilityToken.from_dict(raw)

    now = datetime.now(timezone.utc)
    if now >= token.expires_at:
        return ValidationResult(False, EXPIRED_TOKEN, token_id)

    if action not in token.actions:
        return ValidationResult(False, ACTION_NOT_ALLOWED, token_id)

    if not _scope_allows(token.scope, ctx):
        return ValidationResult(False, INSUFFICIENT_SCOPE, token_id)

    return ValidationResult(True, None, token_id)


def _scope_allows(scope: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    """
    Minimal scope model for A5:
    - If scope contains {"path": "..."} then ctx["path"] must match exactly.
    - If scope contains {"path_prefix": "..."} then ctx["path"] must startwith it.
    - If no recognized scope keys exist, allow (scope is empty / non-path-based).
    """
    if not scope:
        return True

    ctx_path = str(ctx.get("path") or "")

    if "path" in scope:
        return ctx_path == str(scope["path"])

    if "path_prefix" in scope:
        return ctx_path.startswith(str(scope["path_prefix"]))

    # Unknown scope keys: for A5 we allow them (future extension),
    # but callers should use recognized keys for enforcement.
    return True
