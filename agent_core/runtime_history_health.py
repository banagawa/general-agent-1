from __future__ import annotations

from dataclasses import dataclass

from sandbox.mounts import get_runtime_state_root


RUNTIME_HISTORY_SIZE_WARNING = "RUNTIME_HISTORY_SIZE_WARNING"
RUNTIME_HISTORY_FILE_COUNT_WARNING = "RUNTIME_HISTORY_FILE_COUNT_WARNING"

DEFAULT_RUNTIME_HISTORY_SIZE_WARNING_BYTES = 100 * 1024 * 1024
DEFAULT_RUNTIME_HISTORY_FILE_COUNT_WARNING = 10_000


@dataclass(frozen=True)
class RuntimeHistoryHealth:
    root: str
    exists: bool
    total_bytes: int
    file_count: int
    warnings: tuple[str, ...]


def get_runtime_history_health(
    *,
    size_warning_bytes: int = DEFAULT_RUNTIME_HISTORY_SIZE_WARNING_BYTES,
    file_count_warning: int = DEFAULT_RUNTIME_HISTORY_FILE_COUNT_WARNING,
) -> RuntimeHistoryHealth:
    """
    Inspect runtime history size without mutating anything.

    This helper is intentionally read-only. It does not delete, compact,
    archive, migrate, or rewrite runtime history.
    """
    root = get_runtime_state_root()
    files = [path for path in root.rglob("*") if path.is_file()] if root.exists() else []

    total_bytes = sum(path.stat().st_size for path in files)

    warnings: list[str] = []
    if total_bytes >= size_warning_bytes:
        warnings.append(RUNTIME_HISTORY_SIZE_WARNING)
    if len(files) >= file_count_warning:
        warnings.append(RUNTIME_HISTORY_FILE_COUNT_WARNING)

    return RuntimeHistoryHealth(
        root=str(root),
        exists=root.exists(),
        total_bytes=total_bytes,
        file_count=len(files),
        warnings=tuple(warnings),
    )
