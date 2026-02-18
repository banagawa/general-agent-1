from pathlib import Path

class FileSystemTools:
    def search(self, root: Path, query: str):
        matches = []
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".txt", ".md", ".py"}:
                try:
                    content = path.read_text(errors="ignore")
                    if query.lower() in content.lower():
                        matches.append(path)
                except Exception:
                    continue
        return matches

    def read(self, path: Path, max_chars: int = 5000):
        return path.read_text(errors="ignore")[:max_chars]
