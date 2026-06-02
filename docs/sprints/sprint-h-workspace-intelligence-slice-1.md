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
