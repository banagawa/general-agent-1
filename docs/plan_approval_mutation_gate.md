# Plan 1b - Approval Gate Mutation Semantics

## Purpose

Prevent invalid executable plans from reaching execution when their mutation tool does not match the current workspace file state.

This directly addresses the Plan 1 retry failure where a new test file was submitted with `PATCH_APPLY`. Under the repo contract, `PATCH_APPLY` is whole-file replacement for existing files, while `FILE_CREATE` is the only creation tool.

## Gate rules

Before approval succeeds:

- `PATCH_APPLY` target must already exist and be a file.
- `PATCH_EDIT` target must already exist and be a file.
- `FILE_CREATE` target must not already exist.
- `FILE_CREATE` parent directory must already exist.
- mutation paths must be relative, stay inside `workspace_root`, and reject parent traversal.

## Why approval-time

Execution-time failure is safe, but late. Approval-time rejection is better because it prevents spending approval on a plan that cannot possibly execute correctly.

## Alignment

- Preserves ToolGateway choke point.
- Preserves typed mutation split.
- Keeps deny-by-default behavior.
- Does not expand tool surface.
- Does not add new privilege.
- Uses `workspace_root` as mutation authority.
