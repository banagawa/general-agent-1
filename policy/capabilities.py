from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set


def _capability_dir() -> Path:
    from sandbox.mounts import get_runtime_state_root

    return get_runtime_state_root() / "capabilities"


def _tokens_file() -> Path:
    return _capability_dir() / "capability_tokens.json"


def _revocations_file() -> Path:
    return _capability_dir() / "capability_revocations.json"

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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_tokens() -> Dict[str, Dict[str, Any]]:
    # token_id -> token_dict
    return _load_json(_tokens_file(), default={})


def _save_tokens(tokens: Dict[str, Dict[str, Any]]) -> None:
    _save_json(_tokens_file(), tokens)


def _load_revocations() -> Set[str]:
    data = _load_json(_revocations_file(), default={"revoked": []})
    revoked = data.get("revoked", [])
    return set(map(str, revoked))


def _save_revocations(revoked: Set[str]) -> None:
    _save_json(_revocations_file(), {"revoked": sorted(revoked)})


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


def _workspace_bound_path(value: Any) -> Optional[Path]:
    if value is None:
        return None

    raw = str(value)
    if not raw.strip():
        return None

    try:
        from sandbox.mounts import get_workspace_root

        workspace_root = get_workspace_root().resolve()
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = workspace_root / candidate

        resolved = candidate.resolve()
        resolved.relative_to(workspace_root)
        return resolved
    except Exception:
        return None


def _path_scope_allows(scope_value: Any, ctx_value: Any, *, prefix: bool) -> bool:
    expected = _workspace_bound_path(scope_value)
    actual = _workspace_bound_path(ctx_value)

    if expected is None or actual is None:
        return False

    if prefix:
        try:
            actual.relative_to(expected)
            return True
        except ValueError:
            return False

    return actual == expected


def _scope_allows(scope: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    """
    Fail-closed scope model:
    - empty scope is allowed for non-path actions
    - relative path scopes resolve under workspace_root, never cwd
    - absolute path scopes must still resolve inside workspace_root
    - path scope requires exact resolved path match
    - path_prefix scope requires resolved relative_to containment
    - unknown scope keys deny instead of silently allowing
    """
    if not scope:
        return True

    recognized = {"path", "path_prefix"}
    if set(scope.keys()) - recognized:
        return False

    ctx_path = ctx.get("path")

    if "path" in scope:
        return _path_scope_allows(scope["path"], ctx_path, prefix=False)

    if "path_prefix" in scope:
        return _path_scope_allows(scope["path_prefix"], ctx_path, prefix=True)

    return False
