---
description: "Plan or implement a delegated runtime replacement in the Cubecloud fork, such as removing Nanobot, wiring OpenClaw, changing agent ports, or cleaning up external agent registry drift."
name: "Plan External Agent Migration"
argument-hint: "Describe the runtime swap, e.g. 'replace nanobot with openclaw on port 18788'"
agent: agent
tools: [execute, read, edit, search, todo]
---
Use the **External Agent Migration** agent (@external-agent-migration) when the task is to remove, replace, or rewire a delegated runtime or shared external-agent surface.

## Default Behavior

- Start in plan-only mode.
- Inventory the current registry, env, Compose, gateway, docs, and smoke-test surfaces first.
- Report:
  - every place that still refers to the old runtime or old port
  - whether the replacement should be an `acting-agent`, a shared `mcp_servers` entry, or both
  - the smallest coordinated file set required
  - validation steps and rollout risks
- Do not edit Compose, env, registry, gateway, or docs until the user explicitly approves implementation.

## Required Context

For this repo, relevant sources of truth are:

- [openspace/config/external_agents.contract.md](../../openspace/config/external_agents.contract.md)
- [openspace/config/external_agents.json](../../openspace/config/external_agents.json)
- [openspace/host_skills/README.md](../../openspace/host_skills/README.md)
- [docker-compose.yml](../../docker-compose.yml)
- [docker-compose.release.yml](../../docker-compose.release.yml)
- [deploy/local-runtime/docker-compose.yml](../../deploy/local-runtime/docker-compose.yml)
- [INSTALL_FORK_WINDOWS.md](../../INSTALL_FORK_WINDOWS.md)

## Planning Rules

- Treat Nanobot and OpenClaw swaps as coordinated runtime migrations, not a single config rename.
- If the replacement port changes, verify it does not collide with `7788`, `8788`, or `5173`.
- If Docker release paths change, pair the plan with the GHCR release workflow instead of updating only local-build surfaces.
- Escalate instead of guessing when contract shape, protocol type, or MCP-vs-handoff modeling is unclear.