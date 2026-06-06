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
    calls: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    parse_error: str | None = None


@dataclass(frozen=True)
class TestSelection:
    tests: tuple[str, ...]
    run_full_suite: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "tests": list(self.tests),
            "run_full_suite": self.run_full_suite,
            "reasons": list(self.reasons),
        }


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

    def find_file(self, path: str) -> dict | None:
        """Return metadata for a FILE ArtifactID built from a workspace-relative path."""
        return self.find_artifact(artifact_for_file(path))

    def find_module(self, path: str) -> dict | None:
        """Return metadata for a MODULE ArtifactID built from a workspace-relative path."""
        return self.find_artifact(artifact_for_module(path))

    def find_function(self, path: str, symbol: str) -> dict | None:
        """Return metadata for a FUNC ArtifactID built from path and symbol."""
        return self.find_artifact(artifact_for_function(path, symbol))

    def find_test(self, path: str, test_name: str) -> dict | None:
        """Return metadata for a TEST ArtifactID built from path and test name."""
        return self.find_artifact(artifact_for_test(path, test_name))

    def calls_from(self, function: ArtifactID | str) -> tuple[str, ...]:
        """Return direct static call targets for a FUNC ArtifactID."""
        parsed = _require_function_artifact(function, "calls_from")
        source = str(parsed)
        targets = [target for node in self.files for caller, target in node.calls if caller == source]
        return tuple(sorted(set(targets)))

    def called_by(self, function: ArtifactID | str) -> tuple[str, ...]:
        """Return direct static callers for a FUNC ArtifactID."""
        parsed = _require_function_artifact(function, "called_by")
        target = str(parsed)
        callers = [caller for node in self.files for caller, callee in node.calls if callee == target]
        return tuple(sorted(set(callers)))

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
                    "calls": [[caller, target] for caller, target in node.calls],
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


def select_tests_for_changes(
    graph: WorkspaceGraph,
    *,
    changed_paths: Iterable[str] = (),
    changed_functions: Iterable[ArtifactID | str] = (),
    full_suite_on_no_selection: bool = True,
) -> TestSelection:
    """Return advisory test selection for changed paths and functions.

    This is read-only planner intelligence. It does not execute tests, mutate
    plans, grant policy authority, or expand ToolGateway scope. When changes
    are provided but no precise tests are found, the result recommends a full
    suite run instead of pretending narrow selection is sufficient.
    """
    path_changes = tuple(changed_paths)
    function_changes = tuple(changed_functions)

    selected: set[str] = set()
    reasons: list[str] = []

    if path_changes:
        path_tests = impacted_tests_for_modules(graph, path_changes)
        selected.update(path_tests)
        reasons.append("changed_paths")
        if path_tests:
            reasons.append("path_or_module_impacts")

    if function_changes:
        function_tests = impacted_tests_for_functions(graph, function_changes)
        selected.update(function_tests)
        reasons.append("changed_functions")
        if function_tests:
            reasons.append("function_call_impacts")

    has_changes = bool(path_changes or function_changes)
    run_full_suite = bool(full_suite_on_no_selection and has_changes and not selected)

    if not has_changes:
        reasons.append("no_changes")
    elif run_full_suite:
        reasons.append("no_precise_tests_selected")

    return TestSelection(
        tests=tuple(sorted(selected)),
        run_full_suite=run_full_suite,
        reasons=tuple(dict.fromkeys(reasons)),
    )


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


def impacted_tests_for_functions(graph: WorkspaceGraph, changed_functions: Iterable[ArtifactID | str]) -> tuple[str, ...]:
    """Return tests impacted by changed functions through reverse call edges.

    This is advisory only. It does not execute tests, mutate plans, expand tool
    authority, or infer dynamic dispatch. Starting from changed FUNC ArtifactIDs,
    it walks direct static callers until no new callers are found, then returns
    tests whose functions are in the impacted set.
    """
    impacted_functions = _impacted_functions_from_changed_functions(graph, changed_functions)
    if not impacted_functions:
        return ()

    selected: list[str] = []
    for node in graph.files:
        for test_id in node.tests:
            function_id = test_id.replace("TEST::", "FUNC::", 1)
            if function_id in impacted_functions:
                selected.append(test_id)

    return tuple(sorted(set(selected)))


def _impacted_functions_from_changed_functions(
    graph: WorkspaceGraph,
    changed_functions: Iterable[ArtifactID | str],
) -> set[str]:
    pending = [
        str(_require_function_artifact(function, "impacted_tests_for_functions"))
        for function in changed_functions
    ]
    impacted: set[str] = set()

    while pending:
        current = pending.pop(0)
        if current in impacted:
            continue
        impacted.add(current)
        for caller in graph.called_by(current):
            if caller not in impacted:
                pending.append(caller)

    return impacted


def _require_function_artifact(function: ArtifactID | str, caller: str) -> ArtifactID:
    parsed = ArtifactID.parse(function) if isinstance(function, str) else function
    if parsed.kind != "FUNC":
        raise ValueError(f"{caller} requires FUNC artifact")
    return parsed


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


def _collect_call_edges(rel_path: str, tree: ast.AST) -> tuple[tuple[str, str], ...]:
    local_functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    imported_symbols: dict[str, tuple[str, str]] = {}
    module_aliases: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.split(".")[0]
                module_aliases[local_name] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name == "*":
                    continue
                local_name = alias.asname or alias.name
                imported_symbols[local_name] = (node.module, alias.name)

    edges: set[tuple[str, str]] = set()
    for function_node in ast.walk(tree):
        if not isinstance(function_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        source = str(artifact_for_function(rel_path, function_node.name))
        for node in ast.walk(function_node):
            if not isinstance(node, ast.Call):
                continue
            target = _called_artifact_from_expr(
                rel_path,
                node.func,
                local_functions,
                imported_symbols,
                module_aliases,
            )
            if target is not None and target != source:
                edges.add((source, target))

    return tuple(sorted(edges))


def _called_artifact_from_expr(
    rel_path: str,
    expr: ast.expr,
    local_functions: set[str],
    imported_symbols: dict[str, tuple[str, str]],
    module_aliases: dict[str, str],
) -> str | None:
    if isinstance(expr, ast.Name):
        if expr.id in local_functions:
            return str(artifact_for_function(rel_path, expr.id))
        imported = imported_symbols.get(expr.id)
        if imported is not None:
            module_name, symbol = imported
            module_path = _python_path_from_module_name(module_name)
            return str(artifact_for_function(module_path, symbol))

    if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name):
        module_name = module_aliases.get(expr.value.id)
        if module_name is not None:
            module_path = _python_path_from_module_name(module_name)
            return str(artifact_for_function(module_path, expr.attr))

    return None


def _python_path_from_module_name(module_name: str) -> str:
    return f"{module_name.replace('.', '/')}.py"


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

    calls = _collect_call_edges(rel_path, tree)

    return PythonFileNode(
        artifact_id=file_id,
        path=rel_path,
        module_id=module_id,
        imports=tuple(sorted(imports)),
        functions=tuple(sorted(functions)),
        tests=tuple(sorted(tests)),
        calls=calls,
    )
