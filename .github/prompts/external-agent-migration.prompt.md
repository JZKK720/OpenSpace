---
description: "Plan or implement a delegated runtime replacement or standalone app swap in the Cubecloud fork, such as replacing OpenHarness with AgentOS/AionUi on port 3308, removing Nanobot, wiring OpenClaw, changing agent ports, or cleaning up external-agent and standalone-app drift."
name: "Plan External Agent Migration"
argument-hint: "Describe the runtime or app swap, e.g. 'replace openharness with agentos aionui on port 3308'"
agent: agent
tools: [execute, read, edit, search, todo]
---
Use the **External Agent Migration** agent (@external-agent-migration) when the task is to remove, replace, or rewire a delegated runtime or shared external-agent surface.

## Default Behavior

- Start in plan-only mode.
- Inventory the current registry, env, Compose, gateway, docs, and smoke-test surfaces first.
- Report:
  - every place that still refers to the old runtime or old port
  - whether the replacement is a standalone app, an `acting-agent`, a shared `mcp_servers` entry, or a combination
  - whether the dashboard and showcase surfaces are config-driven or need explicit frontend edits
  - the smallest coordinated file set required
  - the required local `.env` and `.env.example` updates for newer app defaults
  - what legacy data or caches are safe to retire versus what needs explicit confirmation
  - whether workflow bundling or import is actually supported by the replacement surface
  - validation steps and rollout risks
- Do not edit Compose, env, registry, gateway, or docs until the user explicitly approves implementation.

## Required Context

For this repo, relevant sources of truth are:

- [openspace/config/standalone_apps.json](../../openspace/config/standalone_apps.json)
- [openspace/config/external_agents.contract.md](../../openspace/config/external_agents.contract.md)
- [openspace/config/external_agents.json](../../openspace/config/external_agents.json)
- [openspace/standalone_apps.py](../../openspace/standalone_apps.py)
- [openspace/host_skills/README.md](../../openspace/host_skills/README.md)
- [frontend/src/api/standaloneApps.ts](../../frontend/src/api/standaloneApps.ts)
- [frontend/src/pages/DashboardPage.tsx](../../frontend/src/pages/DashboardPage.tsx)
- [frontend/src/pages/ShowcasePage.tsx](../../frontend/src/pages/ShowcasePage.tsx)
- [docker-compose.yml](../../docker-compose.yml)
- [docker-compose.release.yml](../../docker-compose.release.yml)
- [deploy/local-runtime/docker-compose.yml](../../deploy/local-runtime/docker-compose.yml)
- [INSTALL_FORK_WINDOWS.md](../../INSTALL_FORK_WINDOWS.md)

## Planning Rules

- Treat OpenHarness and AgentOS/AionUi replacements as coordinated standalone-app migrations, and Nanobot and OpenClaw swaps as coordinated runtime migrations, not single config renames.
- Determine first whether any gateway or external-agent cleanup is actually required. OpenHarness currently appears on standalone-app surfaces; do not delete Python adapters unless inventory shows the old runtime really owns them.
- If the replacement app is already fully config-driven, prefer config and env edits over new dashboard or frontend code.
- Treat local `.env` and `.env.example` updates as part of the implementation slice whenever URLs, ports, or env prefixes change.
- If the replacement port changes, verify it does not collide with `3308`, `7788`, `8788`, or `5173`.
- Inventory stale env vars, docs, and generated runtime data separately. Do not remove `logs/recordings`, `logs/trajectories`, or other caches without confirming ownership and reproducibility.
- If the user wants bundled workflows or tests from the replacement app, verify whether workflows live in OpenSpace recordings, showcase assets, or the external app itself before promising automatic discovery.
- If Docker release paths change, pair the plan with the GHCR release workflow instead of updating only local-build surfaces.
- Escalate instead of guessing when contract shape, protocol type, or MCP-vs-handoff modeling is unclear.