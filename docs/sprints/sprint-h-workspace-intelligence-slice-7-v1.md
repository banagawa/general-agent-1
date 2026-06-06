# Sprint H Slice 7: Intelligent Test Selection

Status: executable implementation slice

## Goal

Add a single deterministic advisory selector that combines existing path/module impact analysis and function-level impact propagation.

## Scope

- Add `TestSelection` as a frozen result object.
- Add `select_tests_for_changes(graph, changed_paths=..., changed_functions=...)`.
- Combine `impacted_tests_for_modules(...)` and `impacted_tests_for_functions(...)`.
- Return deterministic selected test ArtifactIDs.
- Return reason metadata for review.
- Recommend full-suite fallback when changes are present but no precise tests are selected.
- Keep selection advisory-only and read-only.

## Non-goals

- No automatic test execution.
- No new ToolGateway tool.
- No new policy capability.
- No executor or validator change.
- No plan mutation.
- No autonomy change.
- No persistent graph cache.
- No workspace mutation authority based on selector output.

## Security invariant

Intelligent test selection is advisory planner data only. It does not grant permission, skip policy, bypass ToolGateway, execute tests, mutate plans, or authorize workspace mutation.

## Validation

Run:

```text
python -m pytest tests/test_workspace_intelligent_test_selection_slice_7_v1.py -q
python -m pytest -q
```
