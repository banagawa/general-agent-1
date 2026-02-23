# General Agent — Permissioned Internal Execution System

General Agent is a permission-enforced, workspace-bounded execution system designed for controlled file operations and allowlisted command execution.

This is **not** an autonomous agent.  
This is a fail-closed, auditable, policy-driven execution core.

---

## Core Principles

- Deny-by-default
- Workspace-bounded execution
- Patch-only mutation
- Explicit approval for writes
- No shell passthrough
- Auditable lifecycle
- Fail-closed enforcement

---

## Architecture Spine

Orchestrator  
→ AgentLoop  
→ ToolGateway  
→ PolicyEngine  
→ Tool Implementations  

All tool calls must pass through ToolGateway.

There are no direct tool invocations.

# Minimal Architecture Diagram

All execution flows through a single enforcement spine.

User/CLI Request
   |
   v
main.py
   |
   v
Orchestrator
   |
   v
AgentLoop
   |
   v
ToolGateway  <--- single choke point for all tools (audit + policy)
   |
   +--> PolicyEngine (deny-by-default, workspace boundary, deny patterns)
   |
   +--> Tool Implementations
         - FS tools (search/read)
         - Patch write tools (propose/approve)
         - CMD_RUN (allowlisted subprocess, shell=False)
   |
   v
Audit Log (.audit/audit.jsonl)


---

## Critical Invariant

No tool may be invoked directly from the loop or orchestrator.

All actions must pass through:

AgentLoop → ToolGateway → PolicyEngine → Tool

If this invariant is broken, the system’s security model is compromised.

---

## Current Capabilities

### Read-Only Operations
- File search (extension filtered)
- File read (size capped)
- Workspace boundary enforcement
- Persistent audit logging

### Controlled Mutation
- Patch-based writes only
- Proposal + approval flow
- Persistent pending patch store
- Persistent write revocation
- Audit events for propose/approve/deny

### Controlled Command Execution (Sprint A)
- Allowlisted commands only
- argv-only invocation
- shell=False always
- Forced cwd to workspace
- Timeout enforcement
- Output truncation
- Audited allow + deny events

---

## Explicit Non-Goals

- No background execution
- No network connectors
- No self-escalating permissions
- No autonomy
- No full-file overwrite writes
- No unrestricted subprocess usage

---

## Workspace Model

All filesystem access is restricted to:

WORKSPACE_ROOT (configurable via environment variable)

Any path outside this boundary is denied.

---

## Audit Model

Audit log is append-only JSONL at:

.audit/audit.jsonl

Every tool invocation records:
- action
- allow/deny
- timestamp
- structured metadata

Audit is mandatory. Silent execution is forbidden.

---

# Explicit Non-Goals (Current Phase)

- No background execution
- No network connectors
- No self-escalating permissions
- No autonomy
- No unrestricted subprocess usage
- No full-file overwrite writes


---

## Development Status

See:
- docs/anchors/system-state-v1.md
- docs/anchors/architecture-contract.md
- docs/anchors/sprint-history.md
- SECURITY.md

---

## Running

```bash
python main.py "find and summarize: term"
