---
description: "Smoke test or validate a standalone app surface in the Cubecloud fork, such as verifying an OpenHarness to AgentOS/AionUi swap, checking /api/v1/standalone-apps, frontend app cards, health probes, env wiring, and dashboard visibility after config or Compose changes."
name: "Smoke Test Standalone App"
argument-hint: "Describe the app or swap, e.g. 'validate agentos aionui on port 3308 replacing openharness'"
agent: agent
tools: [execute, read, edit, search, todo]
---
Use this prompt when the goal is to verify that a standalone app entry is wired through OpenSpace and appears where expected after a config, env, frontend, or Docker change.

## Parameters

- **App id** (optional): `${input:app:aionui}`
- **Expected port** (optional): `${input:port:3308}`
- **Replaced app id** (optional): `${input:old:openharness}`

## Default Behavior

- Start with a read-only inventory.
- Determine whether the change is config-only or also touches backend or frontend logic.
- Run the smallest validation set that can prove the app is registered, reachable, and still displayed by the dashboard surfaces.
- If the local stack is not running, say so clearly and fall back to config, env, Compose, and consumer-code validation instead of pretending the runtime check passed.

## Source of Truth

- [openspace/config/standalone_apps.json](../../openspace/config/standalone_apps.json)
- [openspace/standalone_apps.py](../../openspace/standalone_apps.py)
- [openspace/dashboard_server.py](../../openspace/dashboard_server.py)
- [frontend/src/api/standaloneApps.ts](../../frontend/src/api/standaloneApps.ts)
- [frontend/src/pages/DashboardPage.tsx](../../frontend/src/pages/DashboardPage.tsx)
- [frontend/src/pages/ShowcasePage.tsx](../../frontend/src/pages/ShowcasePage.tsx)
- [docker-compose.yml](../../docker-compose.yml)
- [docker-compose.release.yml](../../docker-compose.release.yml)
- [deploy/local-runtime/docker-compose.yml](../../deploy/local-runtime/docker-compose.yml)
- [README.md](../../README.md)
- [INSTALL_FORK_WINDOWS.md](../../INSTALL_FORK_WINDOWS.md)

## Validation Rules

- Verify that the new app `id`, name, URLs, env names, and expected port are consistent across config, `.env*`, `frontend/.env*`, Compose, and docs.
- If the migration includes newer app defaults, verify that local `.env` and `.env.example` were updated together before treating runtime failures as app bugs.
- Verify that the replaced app id and env names are either removed or intentionally retained for compatibility; do not leave silent drift.
- Treat dashboard and showcase visibility as data-driven unless code proves otherwise. Check the API path and frontend consumers before proposing UI edits.
- For host-published services used by containers, prefer `host.docker.internal` for internal URLs instead of `localhost`.
- If the change only rewires config, prefer API and build validation over unnecessary code edits.

## Suggested Validation Commands

Run only the commands needed for the touched slice:

```powershell
python -m json.tool openspace/config/standalone_apps.json
git diff -- .env .env.example frontend/.env frontend/.env.example
docker compose config
Invoke-WebRequest http://127.0.0.1:7788/api/v1/standalone-apps -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:7788/api/v1/standalone-apps/aionui -UseBasicParsing
```

Add when frontend standalone app surfaces changed:

```powershell
Set-Location frontend; npm install; npm run build
```

Add when the smoke suite has been extended for standalone apps:

```powershell
python smoke_test_mcp.py --level 1
```

## Output Format

Return these sections in order:

1. Standalone app inventory
2. Validation results
3. Remaining drift
4. Suggested fixes or blockers
