# Cubecloud Fork Install on Windows

This guide installs or updates a Windows machine to the tagged Cubecloud fork redistribution snapshot.

## Release Pin

- Fork repository: `https://github.com/JZKK720/OpenSpace.git`
- Stable tag: `cubecloud-2026.03.29`
- Commit: `cf85e0232c06fc5cb755fbba7aa2bb72c4d80b2f`

## Prerequisites

- Git
- Python 3.12+
- Node.js 20+
- Docker Desktop if you want the packaged dashboard and monitor stack

## Recommended: Docker Rollout Script

This PowerShell script works for both a fresh install and an existing clean clone.

It will:

- clone the fork if needed
- fast-forward local `main` to your fork's `main`
- pin the working tree to `cubecloud-2026.03.29`
- install the Python package
- create `.env` from `.env.example` if needed
- build and start the Docker Compose stack

> If the target machine has local changes, commit or stash them first. The script intentionally stops on a dirty worktree.

```powershell
$ErrorActionPreference = 'Stop'

$RepoUrl = 'https://github.com/JZKK720/OpenSpace.git'
$InstallDir = 'C:\OpenSpace'
$ReleaseTag = 'cubecloud-2026.03.29'

if (-not (Test-Path $InstallDir)) {
    git clone $RepoUrl $InstallDir
}

Set-Location $InstallDir

if (-not (Test-Path '.git')) {
    throw "'$InstallDir' exists but is not a git repository."
}

$dirty = git status --porcelain
if ($dirty) {
    throw 'Working tree is not clean. Commit or stash local changes before running this rollout.'
}

git fetch origin --tags
git fetch origin main
git switch main
git pull --ff-only origin main
git switch --detach $ReleaseTag

python -m pip install -e .

if (-not (Test-Path '.env')) {
    Copy-Item .env.example .env
    Write-Host 'Created .env from .env.example.'
    Write-Host 'Set IRONCLAW_AUTH_TOKEN and GATEWAY_AUTH_TOKEN before using the connected-agent flow.'
}

docker compose up -d --build

Write-Host "Installed $ReleaseTag from $RepoUrl"
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

## Updating to a New Tagged Release Later

When you publish a new redistribution tag on your fork, update the script by replacing:

- `$ReleaseTag = 'cubecloud-2026.03.29'`

with the new tag name.