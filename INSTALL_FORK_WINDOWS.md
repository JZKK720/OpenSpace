# Cubecloud Fork Install on Windows

This guide installs or updates a Windows machine to the tagged Cubecloud fork redistribution snapshot.

## Release Pin

- Fork repository: `https://github.com/JZKK720/OpenSpace.git`
- Latest release: `v0.4.0` (multi-agent gateway, IronClaw + Nanobot + Hermes)
- Tracking branch: `main` (always latest)

## Prerequisites

- Git
- Docker Desktop (required for the container stack)
- Python 3.12+ and Node.js 20+ (only needed for local non-Docker builds)

## Docker Stack — Quick Reference

All four services are managed by `docker compose`. Use `scripts/docker-up.ps1` for the full workflow.

### One-shot install script

The fastest way to get running on a fresh machine:

```powershell
# Download and run the install script directly:
irm https://raw.githubusercontent.com/JZKK720/OpenSpace/main/scripts/install.ps1 | iex
```

Or, if you have already cloned the repo:

```powershell
.\scripts\install.ps1
```

The script will: clone (or pull) the repo, create `.env` from `.env.example`, prompt for your `IRONCLAW_AUTH_TOKEN`, start the Docker stack, and run smoke verification.

### Manual first-time install

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

**Nanobot** (session-based, port 18790) and **Hermes** (OpenAI-compat, port 8789) have working defaults in `.env.example`. Override only if your deployments use different hosts or ports:

```dotenv
# Nanobot — only needed if not running on default port 18790
NANOBOT_INTERNAL_URL=http://host.docker.internal:18790/
NANOBOT_ACTION_URL=http://host.docker.internal:18790/v1/chat/completions

# Hermes — only needed if not running on default port 8789
HERMES_INTERNAL_URL=http://host.docker.internal:8789/
HERMES_ACTION_URL=http://host.docker.internal:8789/v1/chat/completions
HERMES_API_KEY=your_key_if_required
```

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

Just pull the latest `main` branch and re-run docker-up:

```powershell
git pull origin main
.\scripts\docker-up.ps1
```

Or use the install script in update mode (it auto-detects an existing clone and pulls):

```powershell
.\scripts\install.ps1
```