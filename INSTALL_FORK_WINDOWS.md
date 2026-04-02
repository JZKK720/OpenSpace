# Cubecloud Fork Install on Windows

This guide installs or updates a Windows machine to the tagged Cubecloud fork redistribution snapshot.

## Release Pin

- Fork repository: `https://github.com/JZKK720/OpenSpace.git`
- Stable tag: `cubecloud-2026.03.29`
- Tracking branch: `main` (always latest)

## Prerequisites

- Git
- Docker Desktop (required for the container stack)
- Python 3.12+ and Node.js 20+ (only needed for local non-Docker builds)

## Docker Stack — Quick Reference

All four services are managed by `docker compose`. Use `scripts/docker-up.ps1` for the full workflow.

### First-time install

```powershell
git clone https://github.com/JZKK720/OpenSpace.git C:\OpenSpace
Set-Location C:\OpenSpace
Copy-Item .env.example .env        # then edit IRONCLAW_AUTH_TOKEN etc.
.\scripts\docker-up.ps1
```

### Routine update (after `git pull`)

```powershell
.\scripts\docker-up.ps1            # pulls, rebuilds changed images, restarts
```

### Force full rebuild (base-image or dependency change)

```powershell
.\scripts\docker-up.ps1 -Fresh
```

### Wipe containers and rebuild from scratch

```powershell
.\scripts\docker-up.ps1 -Down -Fresh
```

### Build images only (no start)

```powershell
.\scripts\docker-up.ps1 -Build
```

### Check running container status

```powershell
.\scripts\docker-up.ps1 -Status
# or directly:
docker compose ps
```

### Service URLs after stack is up

| Service | URL |
|---|---|
| Cubecloud dashboard | `http://127.0.0.1:7788` |
| Agents monitor | `http://127.0.0.1:5173` |
| OpenSpace runtime MCP | `http://127.0.0.1:8788/mcp` |
| OpenSpace remote MCP | `http://127.0.0.1:8789/mcp` |

### Logs

```powershell
docker compose logs -f                          # all services
docker compose logs -f cubecloud-dashboard      # one service
```

### Stop / teardown

```powershell
docker compose down          # stop and remove containers (keeps volumes)
docker compose down -v       # also remove anonymous volumes
```

## Required `.env` Values

At minimum, set the IronClaw gateway token values in `.env` before relying on delegated agent handoff:

```dotenv
IRONCLAW_AUTH_TOKEN=your_token_here
GATEWAY_AUTH_TOKEN=your_token_here
```

If your IronClaw URLs differ from the defaults in `.env.example`, update those at the same time.

## Verification

After `docker compose up -d --build`, verify the stack:

```powershell
Invoke-WebRequest http://127.0.0.1:7788/api/v1/health -UseBasicParsing
Invoke-RestMethod http://127.0.0.1:7788/api/v1/external-agents
Invoke-RestMethod http://127.0.0.1:7788/api/v1/standalone-apps
docker compose ps
```

Expected dashboard registry results:

- external agent: `ironclaw`
- standalone app: `my-daily-monitor`

## Optional: Local Non-Docker Build

If you want the local build path instead of Docker:

```powershell
Set-Location C:\OpenSpace
git fetch origin --tags
git switch main
git pull --ff-only origin main
git switch --detach cubecloud-2026.03.29

python -m pip install -e .

Push-Location frontend
npm ci
npm run build
Pop-Location

Push-Location showcase/my-daily-monitor
npm ci
npm run build
Pop-Location
```

Then run the services using your preferred local startup flow.

## Optional: Minimize the Local Source Footprint

If you want to keep the containers runnable while moving runtime files out of the full source checkout, use:

```powershell
Set-Location C:\Users\cubecloud006\OpenSpace
.\scripts\prepare_runtime_bundle.ps1 -CopyState
```

By default this exports a minimal runtime bundle to a sibling folder named `OpenSpace-runtime`.

That bundle keeps:

- `.env`
- `docker-compose.yml`
- `openspace/config/external_agents.json`
- `openspace/config/standalone_apps.json`
- optional `.openspace` and `logs` when `-CopyState` is used

Then you can run the stack from that bundle folder with:

```powershell
Set-Location ..\OpenSpace-runtime
docker compose up -d
```

Important: this reduces source exposure in the working checkout, but local Docker images still contain the application code and can be inspected by someone with Docker access on the machine.

## Updating to a New Tagged Release Later

When you publish a new redistribution tag on your fork, update the script by replacing:

- `$ReleaseTag = 'cubecloud-2026.03.29'`

with the new tag name.