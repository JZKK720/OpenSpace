<#
.SYNOPSIS
    Pull and start (or update) the OpenSpace Cubecloud Docker stack.

.DESCRIPTION
    Run from any directory.  Handles first-time setup and incremental updates.

    Modes
    ------
    (default)   Pull latest commits, pull GHCR images, restart containers.
    -LocalBuild Use the checked-in Dockerfiles and rebuild local images instead.
    -Fresh      Force a full no-cache rebuild of every image (requires -LocalBuild).
    -Down       Tear down containers and remove volumes before rebuilding.
    -Build      Build images only; do not start containers (requires -LocalBuild).
    -Status     Show running container status and exit.
    -ImageTag   Pin the GHCR image tag in .env before pulling.

.PARAMETER Fresh
    Rebuild all images from scratch (--no-cache). Requires -LocalBuild.

.PARAMETER Down
    Stop and remove containers + anonymous volumes before pulling or rebuilding.

.PARAMETER Build
    Build images only; skip 'docker compose up'. Requires -LocalBuild.

.PARAMETER Status
    Print container status and exit immediately.

.PARAMETER LocalBuild
    Use the local Dockerfiles and docker-compose.yml instead of GHCR release images.

.PARAMETER ImageTag
    Set OPENSPACE_IMAGE_TAG in .env before running the GHCR release flow.

.EXAMPLE
    # First-time install or routine GHCR update:
    .\scripts\docker-up.ps1

    # Pin a tagged rollout release from GHCR:
    .\scripts\docker-up.ps1 -ImageTag v0.5.0

    # Force full rebuild from local Dockerfiles:
    .\scripts\docker-up.ps1 -LocalBuild -Fresh

    # Just check what's running:
    .\scripts\docker-up.ps1 -Status
#>
param(
    [switch]$Fresh,
    [switch]$Down,
    [switch]$Build,
    [switch]$Status,
    [switch]$LocalBuild,
    [string]$ImageTag = ''
)

$ErrorActionPreference = 'Stop'

# ── Locate repo root ──────────────────────────────────────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

$LocalComposeFile = 'docker-compose.yml'
$ReleaseComposeFile = 'docker-compose.release.yml'
$UseLocalBuild = $LocalBuild

if (-not $UseLocalBuild -and -not (Test-Path $ReleaseComposeFile)) {
    Write-Warning '[docker-up] docker-compose.release.yml was not found — falling back to local build mode.'
    $UseLocalBuild = $true
}

$ComposeFile = if ($UseLocalBuild) { $LocalComposeFile } else { $ReleaseComposeFile }

if (($Fresh -or $Build) -and -not $UseLocalBuild) {
    Write-Error '[docker-up] -Fresh and -Build require -LocalBuild. Use the default mode for GHCR pull-first updates.'
    exit 1
}

function Get-EnvValue($key) {
    if (-not (Test-Path '.env')) {
        return $null
    }

    $line = Select-String -Path '.env' -Pattern "^$key=" | Select-Object -First 1
    if ($line) { return ($line.Line -split '=', 2)[1] }
    return $null
}

function Set-EnvValue($key, $value) {
    $content = Get-Content '.env' -Raw
    if ($content -match "(?m)^$key=") {
        $content = $content -replace "(?m)^$key=.*", "$key=$value"
    } else {
        $content = $content.TrimEnd() + "`n$key=$value`n"
    }
    Set-Content '.env' $content -NoNewline
}

# ── Status only ───────────────────────────────────────────────────────────────
if ($Status) {
    docker compose -f $ComposeFile ps
    exit 0
}

# ── Ensure .env exists ────────────────────────────────────────────────────────
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host '[docker-up] Created .env from .env.example.'
    Write-Host '[docker-up] Edit .env and set IRONCLAW_AUTH_TOKEN / GATEWAY_AUTH_TOKEN before first use.'
}

if ($ImageTag) {
    Set-EnvValue 'OPENSPACE_IMAGE_TAG' $ImageTag
    Write-Host "[docker-up] OPENSPACE_IMAGE_TAG pinned to '$ImageTag' in .env."
}

$effectiveImageTag = Get-EnvValue 'OPENSPACE_IMAGE_TAG'
if (-not $effectiveImageTag) {
    $effectiveImageTag = 'main'
}

# ── Fetch latest commits ──────────────────────────────────────────────────────
$dirty = git status --porcelain
if ($dirty) {
    Write-Warning '[docker-up] Working tree is not clean — skipping git pull. Commit or stash local changes to auto-update.'
} else {
    Write-Host '[docker-up] Pulling latest commits from origin/main ...'
    git fetch origin --tags
    git pull --ff-only origin main
}

# ── Tear down (optional) ──────────────────────────────────────────────────────
if ($Down) {
    Write-Host '[docker-up] Stopping and removing containers ...'
    docker compose -f $ComposeFile down -v
}

# ── Release pull or local build ───────────────────────────────────────────────
if ($UseLocalBuild) {
    $buildArgs = @('compose', '-f', $ComposeFile, 'build')
    if ($Fresh) {
        Write-Host '[docker-up] Full no-cache rebuild ...'
        $buildArgs += '--no-cache'
    } else {
        Write-Host '[docker-up] Building changed images ...'
    }

    $buildArgs += 'openspace-remote-agent', 'openspace-runtime', 'agents-monitor', 'cubecloud-dashboard'
    & docker @buildArgs

    if (-not $?) {
        Write-Error '[docker-up] docker compose build failed. See output above.'
        exit 1
    }

    if (-not $Build) {
        Write-Host '[docker-up] Starting containers from local images ...'
        docker compose -f $ComposeFile up -d --remove-orphans
    } else {
        Write-Host '[docker-up] Local image build complete. Run "docker compose -f docker-compose.yml up -d" to start.'
        exit 0
    }
} else {
    Write-Host "[docker-up] Pulling GHCR release images for tag '$effectiveImageTag' ..."
    docker compose -f $ComposeFile pull

    if (-not $?) {
        Write-Error '[docker-up] docker compose pull failed. Check GHCR access and the requested image tag.'
        exit 1
    }

    Write-Host '[docker-up] Starting containers from GHCR images ...'
    docker compose -f $ComposeFile up -d --remove-orphans
}

if (-not $?) {
    Write-Error '[docker-up] docker compose up failed. See output above.'
    exit 1
}

Write-Host ''
Write-Host '[docker-up] Stack is up. Service URLs:'
Write-Host '  Cubecloud dashboard   http://127.0.0.1:7788'
Write-Host '  Agents monitor        http://127.0.0.1:5173'
Write-Host '  OpenSpace runtime MCP http://127.0.0.1:8788/mcp'
Write-Host '  OpenSpace remote MCP  http://127.0.0.1:8789/mcp'
Write-Host ''
if ($UseLocalBuild) {
    Write-Host '[docker-up] Mode: local build fallback.'
} else {
    Write-Host "[docker-up] Mode: GHCR release pull-first (OPENSPACE_IMAGE_TAG=$effectiveImageTag)."
}
Write-Host '[docker-up] Tip: run with -Status to check container health.'
