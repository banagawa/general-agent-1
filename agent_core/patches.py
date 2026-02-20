from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import uuid

@dataclass(frozen=True)
class PatchProposal:
    patch_id: str
    rel_path: str          # workspace-relative path (string)
    new_content: str
    created_utc: str       # ISO timestamp

def new_patch(rel_path: str, new_content: str) -> PatchProposal:
    pid = uuid.uuid4().hex[:12]
    created = datetime.now(timezone.utc).isoformat()
    return PatchProposal(patch_id=pid, rel_path=rel_path, new_content=new_content, created_utc=created)
