# Sprint H Slice 6: Function-Level Impact Propagation

Status: executable implementation slice

## Goal

Add deterministic advisory test-impact propagation from changed function ArtifactIDs through the reverse static call graph.

## Scope

- Add `impacted_tests_for_functions(graph, changed_functions)`.
- Walk reverse static call edges from changed `FUNC::path::symbol` ArtifactIDs to impacted callers.
- Select tests whose test functions are in the impacted caller set.
- Support direct test callers.
- Support same-file transitive callers.
- Support imported transitive callers already represented by the static call graph.
- Return no impacted tests for unknown but valid function ArtifactIDs.
- Reject non-FUNC, malformed, or unsafe ArtifactIDs fail-closed.
- Keep impact propagation advisory-only and read-only.

## Non-goals

- No automatic test execution outside explicit `TEST_RUN` plan validation steps.
- No new ToolGateway tool.
- No new policy capability.
- No plan mutation.
- No executor or validator change.
- No external indexing service.
- No dynamic dispatch inference.
- No runtime tracing.
- No workspace mutation authority based on impact results.
- No self-mutating behavior.

## Security invariant

Function-level impact propagation is advisory data only. It does not grant permission, skip policy, bypass ToolGateway, change execution behavior, authorize workspace mutation, or make the application self-mutating.

## Validation

Run:

```text
python -m pytest tests/test_workspace_impact_propagation_slice_6_v6.py -q
python -m pytest -q
```
