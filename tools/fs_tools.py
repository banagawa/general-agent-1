from pathlib import Path
import difflib

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB
MAX_CREATE_SIZE_BYTES = 64 * 1024  # 64 KB

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

    def create_file(self, path: Path, content: str) -> str:
        """
        Create a new text file atomically.

        Rules:
        - fail if target already exists
        - fail if parent directory does not exist
        - fail if content is not text
        - fail if content exceeds size cap
        """

        if not isinstance(content, str):
            raise ValueError("content must be string")

        encoded = content.encode("utf-8")
        if len(encoded) > MAX_CREATE_SIZE_BYTES:
            raise ValueError("file too large")

        parent = path.parent
        if not parent.exists():
            raise ValueError("parent directory does not exist")

        if path.exists():
            raise ValueError("file already exists")

        try:
            with open(path, "x", encoding="utf-8") as f:
                f.write(content)
        except FileExistsError:
            raise ValueError("file already exists")

        return str(path)
