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

        # For now: allow only FS_READ
        return action == "FS_READ"

