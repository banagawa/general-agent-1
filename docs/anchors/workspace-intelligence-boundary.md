# Workspace Intelligence Boundary

Status: current operational boundary after Sprint H Slice 7

Workspace intelligence may describe the repository. It must not grant authority.

## Implemented advisory capabilities

- Build a graph from Python files already inside `workspace_root`.
- Treat ArtifactIDs as stable references to repository entities.
- Resolve FILE, MODULE, FUNC, and TEST ArtifactIDs fail-closed.
- Map direct imports and dependency-aware impacted tests.
- Map static function call edges from Python AST.
- Propagate changed function impact through reverse call edges.
- Select impacted tests through `select_tests_for_changes(...)`.
- Recommend full-suite fallback when precise selection is unavailable.
- Log graph rebuild metadata when explicitly requested.

## Forbidden

- Using graph membership as permission to read or write.
- Bypassing ToolGateway, PolicyEngine, or capability checks because an entity appears in the graph.
- Indexing external services or paths outside `workspace_root`.
- Allowing graph rebuilds to mutate source files.
- Treating stale graph data as authority.
- Executing tests from selector output.
- Mutating plans from selector output.
- Granting workspace mutation authority from impacted-test results.

## Invariant

```text
Workspace intelligence is advisory data only.
ToolGateway + PolicyEngine remain the authority boundary.
```

## Validation coverage

- graph build reads only from `workspace_root`.
- graph rebuild is audited when requested.
- graph output never bypasses policy checks.
- ArtifactID resolution fails closed for unsafe paths.
- dependency, call graph, function impact, and test selection results remain read-only.
