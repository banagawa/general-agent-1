from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _audit_dir() -> Path:
    from sandbox.mounts import get_runtime_state_root

    return get_runtime_state_root() / "audit"


def _audit_file() -> Path:
    return _audit_dir() / "audit.jsonl"


def log_event(event: str, meta: Optional[Dict[str, Any]] = None) -> None:
    """
    Backward-compatible audit log writer.

    Writes BOTH schemas in the same record:
      - New:  {timestamp, event, meta}
      - Legacy: {timestamp, action, detail}

    This is additive-only and keeps older log consumers working.
    """
    audit_dir = _audit_dir()
    audit_file = _audit_file()
    audit_dir.mkdir(parents=True, exist_ok=True)

    meta = meta or {}

    entry: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),

        # New schema
        "event": event,
        "meta": meta,

        # Legacy schema (additive)
        "action": event,
        "detail": meta,
    }

    with audit_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
