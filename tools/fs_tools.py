from pathlib import Path
import difflib

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB


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

    def apply_patch(self, path: Path, new_content: str):
        try:
            original = path.read_text(errors="ignore")
            diff = list(difflib.unified_diff(
                original.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile="original",
                tofile="modified",
            ))

            if not diff:
                return "[NO CHANGES DETECTED]"

            path.write_text(new_content)
            return "".join(diff)

        except Exception as e:
            return f"[ERROR applying patch: {e}]"

