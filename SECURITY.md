# SECURITY.md — Control Contract

Status: Governing Document

Purpose:
Define the security control model for the General Agent system.

Goal:
Enable bounded usefulness — the agent can complete real development work
while remaining constrained so it cannot damage the system, exfiltrate data,
or execute uncontrolled actions.

---

## Governing Precedence

If any document conflicts with this file, this file wins.

Related governing docs:

- docs/anchors/security-invariants.md
- docs/anchors/architecture-contract.md
- docs/anchors/system-state-v1.md
- CONTRIBUTING.md

---

## Core Security Invariants

These rules must never weaken.

1. Execution Choke Point

All execution flows through:

Orchestrator → AgentLoop → ToolGateway → PolicyEngine → Tool

2. Deny By Default

Any action not explicitly allowed by policy must be denied.

3. Workspace Boundary

Filesystem access must remain within WORKSPACE_ROOT.

4. Patch Only Mutation

Files may not be overwritten directly.
All mutation must be diff-visible and approval gated.

5. Explicit Approval

Mutating actions require explicit approval.

6. Append Only Audit

All tool actions must log:

- allow
- deny
- failure

Audit logs are append-only.

7. Fail Closed Behavior

Unexpected conditions must deny and log.

---

## Capability Expansion Rule

New capabilities are allowed only if:

- execution remains ToolGateway mediated
- policy gating remains intact
- workspace boundary remains enforced
- mutations remain visible
- actions remain auditable

---

## Network Boundary

Network access is disabled by default.

If introduced, it must:

- be explicitly documented
- be narrowly scoped
- not bypass ToolGateway