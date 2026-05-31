import json
from pathlib import Path
from dataclasses import asdict
from agent_core.patches import PatchProposal

def _pending_dir() -> Path:
    from sandbox.mounts import get_runtime_state_root

    return get_runtime_state_root() / "pending"


def _pending_file() -> Path:
    return _pending_dir() / "pending_patches.json"

def load_pending() -> dict[str, PatchProposal]:
    pending_file = _pending_file()
    if not pending_file.exists():
        return {}
    data = json.loads(pending_file.read_text(encoding="utf-8"))
    return {pid: PatchProposal(**p) for pid, p in data.items()}

def save_pending(pending: dict[str, PatchProposal]) -> None:
    pending_file = _pending_file()
    pending_file.parent.mkdir(parents=True, exist_ok=True)
    data = {pid: asdict(p) for pid, p in pending.items()}
    pending_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
