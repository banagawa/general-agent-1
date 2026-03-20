from __future__ import annotations

import hashlib
from pathlib import Path

from sandbox.mounts import get_workspace_root


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_workspace_fingerprint() -> str:
    workspace = get_workspace_root()
    rows: list[str] = []

    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue

        parts = path.relative_to(workspace).parts

        if parts and parts[0] == "plans":
            continue
        if "__pycache__" in parts:
            continue
        if path.suffix == ".pyc":
            continue

        rel = path.relative_to(workspace).as_posix()
        stat = path.stat()
        file_hash = _hash_file(path)
        rows.append(f"{rel}|{stat.st_size}|{file_hash}")

    payload = "\n".join(rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
