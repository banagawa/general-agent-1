# Workspace Intelligence Boundary

Status: Pre-implementation guardrail for Sprint H

Workspace intelligence may describe the repository. It must not grant authority.

Allowed:

- Build a graph from files already inside `workspace_root`.
- Store derived read-only metadata as auditable artifacts.
- Use graph results to recommend impacted files or tests.
- Treat ArtifactIDs as stable references to repository entities.

Forbidden:

- Using graph membership as permission to read or write.
- Bypassing ToolGateway, PolicyEngine, or capability checks because an entity appears in the graph.
- Indexing external services or paths outside `workspace_root`.
- Allowing graph rebuilds to mutate source files.
- Treating stale graph data as authority.

Invariant:

```text
Workspace intelligence is advisory data only.
ToolGateway + PolicyEngine remain the authority boundary.
```

Required tests before Sprint H implementation:

- graph build reads only from `workspace_root`
- graph rebuild is audited
- graph output never bypasses policy checks
- ArtifactID resolution fails closed when target is outside `workspace_root`
