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


    def find_artifact(self, artifact: ArtifactID | str) -> dict | None:
        """Return deterministic metadata for an ArtifactID, or None when absent.

        Lookup is advisory only. Malformed ArtifactIDs fail closed by raising
        ValueError through ArtifactID.parse. Unknown but valid ArtifactIDs return
        None and do not trigger execution, mutation, policy, or capability flow.
        """
        parsed = ArtifactID.parse(artifact) if isinstance(artifact, str) else artifact
        target = str(parsed)

        for node in self.files:
            if parsed.kind == "FILE" and node.artifact_id == target:
                return _artifact_lookup_record(parsed, node)
            if parsed.kind == "MODULE" and node.module_id == target:
                return _artifact_lookup_record(parsed, node)
            if parsed.kind == "FUNC" and target in node.functions:
                return _artifact_lookup_record(parsed, node)
            if parsed.kind == "TEST" and target in node.tests:
                return _artifact_lookup_record(parsed, node)

        return None

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


def impacted_tests_for_modules(graph: WorkspaceGraph, changed_paths: Iterable[str]) -> tuple[str, ...]:
    """Return test ArtifactIDs whose files directly import changed Python modules.

    This is advisory only. It does not execute tests, mutate plans, or expand
    tool authority. The result is deterministic and intentionally conservative:
    it includes tests in changed test files plus tests in files that directly
    import modules mapped from changed Python paths.
    """
    normalized_paths = {_normalize_changed_path(item) for item in changed_paths}
    changed_modules = set()

    for changed_path in normalized_paths:
        module_name = _module_name_from_python_path(changed_path)
        if module_name is not None:
            changed_modules.add(module_name)

    selected: list[str] = list(impacted_tests_for_paths(graph, normalized_paths))

    if not changed_modules:
        return tuple(sorted(set(selected)))

    for node in graph.files:
        if not node.tests:
            continue
        if node.path in normalized_paths:
            continue
        if any(imported in changed_modules for imported in node.imports):
            selected.extend(node.tests)

    return tuple(sorted(set(selected)))


def _artifact_lookup_record(artifact: ArtifactID, node: PythonFileNode) -> dict:
    return {
        "artifact_id": str(artifact),
        "kind": artifact.kind,
        "path": artifact.path,
        "symbol": artifact.symbol,
        "file_artifact_id": node.artifact_id,
        "module_id": node.module_id,
        "parse_error": node.parse_error,
    }


def _normalize_changed_path(path: str) -> str:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("changed path must be non-empty string")
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    if normalized.startswith("/") or normalized.startswith("//"):
        raise ValueError("changed path must be workspace-relative")
    if len(path) >= 2 and path[1] == ":":
        raise ValueError("changed path must not include drive letters")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("changed path must not contain empty, dot, or parent parts")
    return normalized


def _module_name_from_python_path(path: str) -> str | None:
    if not path.endswith(".py"):
        return None
    module_path = path[:-3]
    if module_path.endswith("/__init__"):
        module_path = module_path[: -len("/__init__")]
    if not module_path:
        return None
    return module_path.replace("/", ".")


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
