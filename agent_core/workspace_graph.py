from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .artifact_id import ArtifactID, artifact_for_file, artifact_for_function, artifact_for_module, artifact_for_test

_EXCLUDED_DIRS = {".git", ".audit", ".pytest_cache", "__pycache__", "agent_runtime"}


@dataclass(frozen=True)
class PythonFileNode:
    artifact_id: str
    path: str
    module_id: str
    imports: tuple[str, ...] = field(default_factory=tuple)
    functions: tuple[str, ...] = field(default_factory=tuple)
    tests: tuple[str, ...] = field(default_factory=tuple)
    parse_error: str | None = None


@dataclass(frozen=True)
class WorkspaceGraph:
    root: str
    files: tuple[PythonFileNode, ...]

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def function_count(self) -> int:
        return sum(len(item.functions) for item in self.files)

    @property
    def test_count(self) -> int:
        return sum(len(item.tests) for item in self.files)

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "files": [
                {
                    "artifact_id": node.artifact_id,
                    "path": node.path,
                    "module_id": node.module_id,
                    "imports": list(node.imports),
                    "functions": list(node.functions),
                    "tests": list(node.tests),
                    "parse_error": node.parse_error,
                }
                for node in self.files
            ],
            "summary": {
                "file_count": self.file_count,
                "function_count": self.function_count,
                "test_count": self.test_count,
            },
        }


def build_workspace_graph(workspace_root: Path | None = None, *, audit_rebuild: bool = False) -> WorkspaceGraph:
    if workspace_root is None:
        from sandbox.mounts import get_workspace_root

        root = get_workspace_root().resolve()
    else:
        root = workspace_root.resolve()

    if not root.exists() or not root.is_dir():
        raise ValueError("workspace_root must be an existing directory")

    files = tuple(_scan_python_file(root, path) for path in _iter_python_files(root))
    graph = WorkspaceGraph(root=str(root), files=files)

    if audit_rebuild:
        from audit.log import log_event

        log_event(
            "WORKSPACE_GRAPH_REBUILT",
            {
                "workspace_root": str(root),
                "file_count": graph.file_count,
                "function_count": graph.function_count,
                "test_count": graph.test_count,
            },
        )

    return graph


def impacted_tests_for_paths(graph: WorkspaceGraph, changed_paths: Iterable[str]) -> tuple[str, ...]:
    normalized = {item.replace("\\", "/") for item in changed_paths}
    selected: list[str] = []
    for node in graph.files:
        if node.path in normalized and node.tests:
            selected.extend(node.tests)
    return tuple(sorted(set(selected)))


def _iter_python_files(root: Path) -> tuple[Path, ...]:
    result: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in _EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("python file resolved outside workspace")
        result.append(resolved)
    return tuple(sorted(result, key=lambda item: item.relative_to(root).as_posix()))


def _scan_python_file(root: Path, path: Path) -> PythonFileNode:
    rel_path = path.relative_to(root).as_posix()
    file_id = str(artifact_for_file(rel_path))
    module_id = str(artifact_for_module(rel_path))

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
    except (SyntaxError, UnicodeDecodeError) as exc:
        return PythonFileNode(
            artifact_id=file_id,
            path=rel_path,
            module_id=module_id,
            parse_error=f"{exc.__class__.__name__}: {exc}",
        )

    imports: set[str] = set()
    functions: list[str] = []
    tests: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_id = str(artifact_for_function(rel_path, node.name))
            functions.append(func_id)
            if rel_path.startswith("tests/") and node.name.startswith("test_"):
                tests.append(str(artifact_for_test(rel_path, node.name)))

    return PythonFileNode(
        artifact_id=file_id,
        path=rel_path,
        module_id=module_id,
        imports=tuple(sorted(imports)),
        functions=tuple(sorted(functions)),
        tests=tuple(sorted(tests)),
    )
