from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import difflib


MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB


@dataclass(frozen=True)
class PatchEditError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


class FileSystemTools:
    def search(self, root: Path, query: str, max_results: int = 50):
        matches = []
        for path in root.rglob("*"):
            if len(matches) >= max_results:
                break

            if path.is_file() and path.suffix in {".txt", ".md", ".py"}:
                try:
                    if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                        continue

                    content = path.read_text(errors="ignore")
                    if query.lower() in content.lower():
                        matches.append(path)
                except Exception:
                    continue

        return matches

    def read(self, path: Path, max_chars: int = 5000):
        try:
            if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                return "[SKIPPED: file too large]"
            return path.read_text(errors="ignore")[:max_chars]
        except Exception:
            return "[ERROR: unable to read file]"

    def preview_diff(self, original: str, new_content: str) -> str:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile="original",
            tofile="proposed",
        )
        out = "".join(diff)
        return out if out.strip() else "[NO CHANGES DETECTED]"

    def apply_patch(self, path: Path, new_content: str):
        try:
            original = path.read_text(errors="ignore")
            diff = list(
                difflib.unified_diff(
                    original.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile="original",
                    tofile="modified",
                )
            )

            if not diff:
                return "[NO CHANGES DETECTED]"

            path.write_text(new_content)
            return "".join(diff)

        except Exception as e:
            return f"[ERROR applying patch: {e}]"

    def patch_edit(
        self,
        path: Path,
        edits: list[dict],
        expected_file_sha256_before: str | None = None,
    ) -> dict:
        if not path.exists():
            raise PatchEditError("PATCH_EDIT_TARGET_MISSING")

        if not path.is_file():
            raise PatchEditError("PATCH_EDIT_TARGET_NOT_FILE")

        try:
            if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                raise PatchEditError("PATCH_EDIT_FILE_TOO_LARGE")
        except OSError as e:
            raise PatchEditError(f"PATCH_EDIT_STAT_FAILED: {e}") from e

        try:
            original = path.read_text(encoding="utf-8")
        except Exception as e:
            raise PatchEditError(f"PATCH_EDIT_READ_FAILED: {e}") from e

        original_sha256 = sha256(original.encode("utf-8")).hexdigest()

        if expected_file_sha256_before is not None:
            if original_sha256 != expected_file_sha256_before:
                raise PatchEditError("PATCH_EDIT_HASH_MISMATCH")

        updated = original

        for index, edit in enumerate(edits, start=1):
            old_text = edit["old_text"]
            new_text = edit["new_text"]
            occurrence = edit.get("occurrence")

            updated = self._apply_single_edit(
                content=updated,
                old_text=old_text,
                new_text=new_text,
                occurrence=occurrence,
                edit_index=index,
            )

        if updated == original:
            diff_text = "[NO CHANGES DETECTED]"
        else:
            diff_text = "".join(
                difflib.unified_diff(
                    original.splitlines(keepends=True),
                    updated.splitlines(keepends=True),
                    fromfile="original",
                    tofile="modified",
                )
            )

        try:
            path.write_text(updated, encoding="utf-8")
        except Exception as e:
            raise PatchEditError(f"PATCH_EDIT_WRITE_FAILED: {e}") from e

        return {
            "ok": True,
            "path": str(path),
            "edit_count": len(edits),
            "changed": updated != original,
            "diff": diff_text if diff_text.strip() else "[NO CHANGES DETECTED]",
            "sha256_before": original_sha256,
            "sha256_after": sha256(updated.encode("utf-8")).hexdigest(),
        }

    def _apply_single_edit(
        self,
        *,
        content: str,
        old_text: str,
        new_text: str,
        occurrence: int | None,
        edit_index: int,
    ) -> str:
        if old_text == new_text:
            return content
        if old_text == "":
            raise PatchEditError(f"PATCH_EDIT_EMPTY_OLD_TEXT_AT_{edit_index}")

        positions = []
        start = 0

        while True:
            pos = content.find(old_text, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + len(old_text)

        if len(positions) == 0:
            raise PatchEditError(f"PATCH_EDIT_OLD_TEXT_NOT_FOUND_AT_{edit_index}")

        if occurrence is None:
            if len(positions) != 1:
                raise PatchEditError(f"PATCH_EDIT_AMBIGUOUS_MATCH_AT_{edit_index}")
            chosen = positions[0]
        else:
            if occurrence < 1 or occurrence > len(positions):
                raise PatchEditError(f"PATCH_EDIT_OCCURRENCE_OUT_OF_RANGE_AT_{edit_index}")
            chosen = positions[occurrence - 1]

        end = chosen + len(old_text)
        return content[:chosen] + new_text + content[end:]
