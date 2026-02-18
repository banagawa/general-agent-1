import json
from datetime import datetime
from pathlib import Path

AUDIT_DIR = Path(".audit")
AUDIT_DIR.mkdir(exist_ok=True)

AUDIT_FILE = AUDIT_DIR / "audit.jsonl"

def log_event(action: str, detail: str):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "detail": detail,
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

