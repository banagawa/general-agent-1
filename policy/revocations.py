import json
from pathlib import Path

REVOCATION_FILE = Path(".audit/revocations.json")

def _load():
    if not REVOCATION_FILE.exists():
        return {"writes_revoked": False}
    return json.loads(REVOCATION_FILE.read_text(encoding="utf-8"))

def _save(data: dict):
    REVOCATION_FILE.parent.mkdir(exist_ok=True)
    REVOCATION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def writes_revoked() -> bool:
    return _load().get("writes_revoked", False)

def revoke_writes():
    data = _load()
    data["writes_revoked"] = True
    _save(data)
