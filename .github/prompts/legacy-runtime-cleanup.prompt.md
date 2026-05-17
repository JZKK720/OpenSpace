---
description: "Inventory and retire legacy runtime artifacts in the Cubecloud fork, such as removing stale OpenHarness env vars, Compose wiring, dashboard entries, docs, cached recordings, or generated runtime data after a swap to AgentOS/AionUi or another replacement."
name: "Plan Legacy Runtime Cleanup"
argument-hint: "Describe the retired runtime and replacement, e.g. 'clean openharness after moving to agentos aionui'"
agent: agent
tools: [execute, read, edit, search, todo]
---
Use this prompt when the goal is to clean stale configuration, docs, caches, or generated artifacts left behind after a runtime or standalone app migration.

## Default Behavior

- Start in plan-only mode.
- Inventory stale references in config, env, Compose, frontend env, docs, logs, and generated outputs.
- Classify every hit as one of:
  - safe config or doc cleanup
  - generated artifact that needs explicit confirmation
  - likely user data or workflow evidence that should not be deleted blindly
- Report the exact cleanup set before deleting anything outside trivial config and doc surfaces.

## Source of Truth

- [openspace/config/standalone_apps.json](../../openspace/config/standalone_apps.json)
- [openspace/config/external_agents.json](../../openspace/config/external_agents.json)
- [openspace/dashboard_server.py](../../openspace/dashboard_server.py)
- [frontend/src/api/standaloneApps.ts](../../frontend/src/api/standaloneApps.ts)
- [frontend/src/pages/DashboardPage.tsx](../../frontend/src/pages/DashboardPage.tsx)
- [frontend/src/pages/ShowcasePage.tsx](../../frontend/src/pages/ShowcasePage.tsx)
- [docker-compose.yml](../../docker-compose.yml)
- [docker-compose.release.yml](../../docker-compose.release.yml)
- [deploy/local-runtime/docker-compose.yml](../../deploy/local-runtime/docker-compose.yml)
- [README.md](../../README.md)
- [INSTALL_FORK_WINDOWS.md](../../INSTALL_FORK_WINDOWS.md)
- [logs/recordings](../../logs/recordings)
- [logs/dashboard_server](../../logs/dashboard_server)
- [logs/mcp_server](../../logs/mcp_server)
- [logs/openspace](../../logs/openspace)

## Planning Rules

- Search by runtime id, product name, env prefix, port, and known URLs.
- Treat local `.env` and `.env.example` as coordinated cleanup and migration surfaces for newer app updates; do not retire old env keys in only one file.
- Separate config and doc cleanup from generated runtime data cleanup; they do not carry the same deletion risk.
- Never remove non-trivial artifacts under `logs/`, `showcase/`, `deploy/`, or imported workflow bundles without explicit confirmation.
- If the user asks to remove caches or legacy data, prove ownership first. Directory age or name similarity alone is not enough.
- If workflow bundles are part of the request, determine whether they live in OpenSpace recordings, showcase assets, external-app exports, or not in the repo at all before planning deletion or tests.

## Suggested Inventory Commands

Run only the commands needed for the stale surface inventory:

```powershell
git grep -n "openharness\|agentos\|aionui\|OPENHARNESS_\|AGENTOS_\|AIONUI_" -- . ":!frontend/dist"
git diff -- .env .env.example frontend/.env frontend/.env.example
Get-ChildItem logs/recordings -Directory | Select-Object -First 50 Name
python -m json.tool openspace/config/standalone_apps.json
python -m json.tool openspace/config/external_agents.json
docker compose config
```

## Output Format

Return these sections in order:

1. Stale runtime inventory
2. Safe cleanup set
3. Confirmation-required cleanup
4. Validation or follow-up checks
5. Blockers or unknown ownership
