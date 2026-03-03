# Sprint C — Repo Kernel

## Objective
Introduce a safe, minimal git execution surface via GIT_RUN.

## Allowed Subcommands
- init
- status
- diff
- add
- commit
- log

## Denied Categories
- Remote/network operations
- Branch manipulation
- Submodules
- Config overrides
- Unknown flags

## Mutation Model
Mutating:
- init
- add
- commit

Requires capability token.

Read-only:
- status
- diff
- log

## Enforcement
- ToolGateway choke point
- PolicyEngine allowlist
- shell=False execution
- Forced workspace cwd
- Audit events:
  - GIT_RUN_DENIED
  - GIT_RUN_EXECUTED

## Test Requirements
- Allow tests for each allowed subcommand
- Deny tests for remote/branch ops
- Deny tests for forbidden flags
- Audit verification for allow + deny
