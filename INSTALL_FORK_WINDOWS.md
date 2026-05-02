# Cubecloud Fork Install on Windows

This guide installs or updates a Windows machine to the tagged Cubecloud fork redistribution snapshot.

## Release Pin

- Fork repository: `https://github.com/JZKK720/OpenSpace.git`
- Rolling GHCR channel: `main`
- GHCR rollout release tag: `v0.6.0` (publish this tag from `origin/main` to cut the next pinned pull-first release)
- Tracking branch: `main` (always latest fork baseline)

## Prerequisites

- Git
- Docker Desktop (required for the container stack)
- Python 3.12+ and Node.js 20+ (only needed for local non-Docker builds)

## Docker Stack — Quick Reference

All four services are managed by `docker compose`. The default workflow now pulls published GHCR images with `scripts/docker-up.ps1`; pass `-LocalBuild` only when you intentionally want to rebuild from the local checkout.

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

The script will: clone (or pull) the repo, create `.env` from `.env.example`, optionally pin `OPENSPACE_IMAGE_TAG`, prompt for your `IRONCLAW_AUTH_TOKEN`, start the Docker stack, and run smoke verification.

### Manual first-time install

```powershell
git clone https://github.com/JZKK720/OpenSpace.git C:\OpenSpace
Set-Location C:\OpenSpace
Copy-Item .env.example .env        # then edit IRONCLAW_AUTH_TOKEN etc.
.\scripts\docker-up.ps1
```

### Routine update (pull latest code, pull latest published images, restart)

```powershell
.\scripts\docker-up.ps1
```

### Pin a tagged release instead of the rolling `main` channel

```powershell
.\scripts\install.ps1 -ImageTag v0.6.0
# or later:
.\scripts\docker-up.ps1 -ImageTag v0.6.0
```

### Local-build fallback (base-image or dependency change)

```powershell
.\scripts\docker-up.ps1 -LocalBuild -Fresh
```

### Wipe containers and rebuild from scratch

```powershell
.\scripts\docker-up.ps1 -LocalBuild -Down -Fresh
```

### Build images only (no start)

```powershell
.\scripts\docker-up.ps1 -LocalBuild -Build
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
| OpenSpace remote MCP | internal-only via `openspace-remote-agent:8080/mcp` |

### Logs

```powershell
docker compose -f docker-compose.release.yml logs -f                     # all services
docker compose -f docker-compose.release.yml logs -f cubecloud-dashboard # one service
```

### Stop / teardown

```powershell
docker compose -f docker-compose.release.yml down          # stop containers, keep volumes
docker compose -f docker-compose.release.yml down -v       # also remove anonymous volumes
```

## Required `.env` Values

At minimum, set the IronClaw gateway token values in `.env` before relying on delegated agent handoff:

```dotenv
IRONCLAW_AUTH_TOKEN=your_token_here
GATEWAY_AUTH_TOKEN=your_token_here
```

**OpenClaw** (OpenAI-compatible gateway, port 18788) and **Hermes** (OpenAI-compat, port 8789) have working defaults in `.env.example`. Override only if your deployments use different hosts or ports:

```dotenv
# OpenClaw — only needed if not running on default port 18788 or if you need to set the gateway token
OPENCLAW_INTERNAL_URL=http://host.docker.internal:18788/
OPENCLAW_ACTION_URL=http://host.docker.internal:18788/v1/chat/completions
OPENCLAW_AUTH_TOKEN=your_openclaw_gateway_token

# Optional: if OpenClaw itself uses host Ollama and host.docker.internal is flaky,
# docker-up.ps1 will write this into /home/node/.openclaw/openclaw.json and restart the gateway.
OPENCLAW_OLLAMA_BASE_URL=http://192.168.65.254:11434

# Hermes — only needed if not running on default port 8789
HERMES_INTERNAL_URL=http://host.docker.internal:8789/
HERMES_ACTION_URL=http://host.docker.internal:8789/v1/chat/completions
HERMES_API_KEY=your_key_if_required
```

For GHCR-based updates, `.env` also controls which published images are used:

```dotenv
OPENSPACE_IMAGE_REGISTRY=ghcr.io/jzkk720
OPENSPACE_IMAGE_TAG=main
```

Set `OPENSPACE_IMAGE_TAG=v0.6.0` after the tag is published if you want to pin this machine to the GHCR rollout release instead of the rolling `main` channel.

## Verification

After `docker compose up -d`, verify the stack:

```powershell
Invoke-WebRequest http://127.0.0.1:7788/api/v1/health -UseBasicParsing
Invoke-RestMethod http://127.0.0.1:7788/api/v1/external-agents
Invoke-RestMethod http://127.0.0.1:7788/api/v1/standalone-apps
docker compose -f docker-compose.release.yml ps
```

Expected dashboard registry results:

- external agents: `ironclaw`, `openclaw`, `hermes`
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

Important: this reduces source exposure in the working checkout, but pulled Docker images still contain the application code and can be inspected by someone with Docker access on the machine.

## Updating to a New Tagged Release Later

To stay on the rolling channel, just pull the latest `main` branch and re-run docker-up:

```powershell
git pull origin main
.\scripts\docker-up.ps1
```

To pin a published release tag from `origin/main`, set `OPENSPACE_IMAGE_TAG` in `.env` or pass `-ImageTag`:

```powershell
.\scripts\docker-up.ps1 -ImageTag v0.6.0
```

Or use the install script in update mode (it auto-detects an existing clone and pulls):

```powershell
.\scripts\install.ps1
```