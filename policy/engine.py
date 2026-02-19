from pathlib import Path
from sandbox.mounts import WORKSPACE_ROOT

DENY_PATTERNS = [".env", "secrets", "credentials"]

class PolicyEngine:
    def is_allowed(self, action: str, path: Path) -> bool:
        try:
            resolved = path.resolve()
        except Exception:
            return False

        # Must be inside workspace (SAFE version)
        try:
            resolved.relative_to(WORKSPACE_ROOT)
        except ValueError:
            return False

        # Basic deny patterns
        for pattern in DENY_PATTERNS:
            if pattern in str(resolved):
                return False

        # Day 4: allow read, search, and patch-based writes
        if action not in ("FS_READ", "FS_SEARCH", "FS_WRITE_PATCH"):
            return False

        return True

