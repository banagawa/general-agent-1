from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


AUDIT_DIR = Path(".audit")
AUDIT_FILE = AUDIT_DIR / "audit.jsonl"

def log_event(event: str, meta: Dict[str, Any] | None = None) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "meta": meta or {}
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

