# Sprint H Slice 1: Workspace Intelligence Foundation

Status: executable implementation slice

## Goal

Add read-only repository intelligence primitives without expanding tool authority.

## Scope

- ArtifactID parsing and formatting for stable repository entities.
- Workspace graph builder for Python files inside the workspace root.
- Advisory impacted-test selector for changed test files.
- Audited graph rebuild event.

## Non-goals

- No new ToolGateway tool.
- No new policy capability.
- No external indexing service.
- No write authority based on graph membership.
- No autonomous refactor execution.

## Security invariant

Workspace intelligence is advisory data only. ToolGateway, policy checks, workspace boundary checks, patch-only writes, and append-only audit remain authoritative.

## Validation

Run:

```text
python -m pytest tests/test_artifact_id.py tests/test_workspace_graph.py -q
python -m pytest -q
```


# Sprint H Slice 2: Dependency Impact Analysis

Status: executable implementation slice

## Goal

Extend the read-only workspace graph with dependency-aware impacted test selection.

## Scope

- Map changed Python file paths to module import names.
- Select tests in files that directly import changed modules.
- Preserve changed-test-file selection from Slice 1.
- Reject unsafe changed paths fail-closed.

## Non-goals

- No automatic test execution.
- No new ToolGateway tool.
- No new policy capability.
- No plan mutation.
- No external indexing service.
- No refactor engine.

## Security invariant

Impact analysis is advisory data only. It can recommend which tests are likely relevant, but it does not alter execution, approval, policy, capabilities, ToolGateway behavior, or workspace mutation rules.

## Validation

Run:

```text
python -m pytest tests/test_workspace_graph.py tests/test_workspace_impact_analysis.py -q
python -m pytest -q
```


# Sprint H Slice 3: Artifact Lookup Index

Status: executable implementation slice

## Goal

Add deterministic ArtifactID lookup on top of the read-only workspace graph.

## Scope

- Resolve FILE, MODULE, FUNC, and TEST ArtifactIDs against the graph.
- Return stable metadata for known artifacts.
- Return None for unknown but valid ArtifactIDs.
- Reject malformed ArtifactIDs fail-closed.
- Keep lookup advisory-only and read-only.

## Non-goals

- No automatic test execution.
- No new ToolGateway tool.
- No new policy capability.
- No plan mutation.
- No executor or validator change.
- No external indexing service.
- No write authority based on graph membership.

## Security invariant

Artifact lookup is advisory data only. A successful lookup does not grant permission, skip policy, bypass ToolGateway, change execution behavior, or authorize workspace mutation.

## Validation

Run:

```text
python -m pytest tests/test_workspace_graph.py tests/test_workspace_impact_analysis.py tests/test_workspace_artifact_index.py -q
python -m pytest -q
```


# Sprint H Slice 4: Graph Query Helpers

Status: executable implementation slice

## Goal

Add small, deterministic convenience query APIs over the existing ArtifactID lookup index.

## Scope

- Add graph.find_file(path).
- Add graph.find_module(path).
- Add graph.find_function(path, symbol).
- Add graph.find_test(path, test_name).
- Keep graph.find_artifact(...) as the shared lookup implementation.
- Add tests for successful lookup, missing lookup, unsafe input rejection, and read-only behavior.

## Non-goals

- No automatic test execution.
- No new ToolGateway tool.
- No new policy capability.
- No plan mutation.
- No executor or validator change.
- No external indexing service.
- No workspace mutation authority based on graph query results.

## Security invariant

Graph query helpers are advisory data only. A successful lookup does not grant permission, skip policy, bypass ToolGateway, change execution behavior, or authorize workspace mutation.

## Validation

Run:

```text
python -m pytest tests/test_workspace_graph_queries.py -q
python -m pytest -q
```


# Sprint H Slice 5: Static Call Graph Mapping

Status: executable implementation slice

## Goal

Add deterministic read-only call graph extraction for Python functions.

## Scope

- Record direct function call edges discovered from Python AST.
- Support same-file function calls.
- Support imported function calls from `from module import symbol`.
- Support imported module attribute calls from `import module as alias`.
- Add `graph.calls_from(function_artifact)`.
- Add `graph.called_by(function_artifact)`.
- Keep call graph data advisory-only and read-only.

## Non-goals

- No runtime tracing.
- No dynamic dispatch inference.
- No automatic test execution.
- No new ToolGateway tool.
- No new policy capability.
- No plan mutation.
- No executor or validator change.
- No external indexing service.
- No workspace mutation authority based on call graph results.

## Security invariant

Call graph mapping is advisory data only. A discovered call edge does not grant permission, skip policy, bypass ToolGateway, change execution behavior, or authorize workspace mutation.

## Validation

Run:

```text
python -m pytest tests/test_workspace_call_graph.py -q
python -m pytest -q
```
