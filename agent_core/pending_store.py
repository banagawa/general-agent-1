import json
from pathlib import Path
from dataclasses import asdict
from agent_core.patches import PatchProposal

PENDING_DIR = Path(".audit")
PENDING_DIR.mkdir(exist_ok=True)
PENDING_FILE = PENDING_DIR / "pending_patches.json"

def load_pending() -> dict[str, PatchProposal]:
    if not PENDING_FILE.exists():
        return {}
    data = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    return {pid: PatchProposal(**p) for pid, p in data.items()}

def save_pending(pending: dict[str, PatchProposal]) -> None:
    data = {pid: asdict(p) for pid, p in pending.items()}
    PENDING_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
