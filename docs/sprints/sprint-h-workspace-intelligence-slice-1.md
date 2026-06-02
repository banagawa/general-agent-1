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
