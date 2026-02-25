from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


AUDIT_DIR = Path(".audit")
AUDIT_FILE = AUDIT_DIR / "audit.jsonl"


def log_event(event: str, meta: Optional[Dict[str, Any]] = None) -> None:
    """
    Backward-compatible audit log writer.

    Writes BOTH schemas in the same record:
      - New:  {timestamp, event, meta}
      - Legacy: {timestamp, action, detail}

    This is additive-only and keeps older log consumers working.
    """
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

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

    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
