<#
.SYNOPSIS
    Build and start (or update) the OpenSpace Cubecloud Docker stack.

.DESCRIPTION
    Run from any directory.  Handles first-time setup and incremental updates.

    Modes
    ------
    (default)   Pull latest commits, rebuild changed images, restart containers.
    -Fresh      Force a full no-cache rebuild of every image.
    -Down       Tear down containers and remove volumes before rebuilding.
    -Build      Build images only; do not start containers.
    -Status     Show running container status and exit.

.PARAMETER Fresh
    Rebuild all images from scratch (--no-cache).

.PARAMETER Down
    Stop and remove containers + anonymous volumes before rebuilding.

.PARAMETER Build
    Build images only; skip 'docker compose up'.

.PARAMETER Status
    Print container status and exit immediately.

.EXAMPLE
    # First-time install or routine update:
    .\scripts\docker-up.ps1

    # Force full rebuild (e.g. after base-image changes):
    .\scripts\docker-up.ps1 -Fresh

    # Wipe containers then rebuild:
    .\scripts\docker-up.ps1 -Down -Fresh

    # Just check what's running:
    .\scripts\docker-up.ps1 -Status
#>
param(
    [switch]$Fresh,
    [switch]$Down,
    [switch]$Build,
    [switch]$Status
)

$ErrorActionPreference = 'Stop'

# ── Locate repo root ──────────────────────────────────────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# ── Status only ───────────────────────────────────────────────────────────────
if ($Status) {
    docker compose ps
    exit 0
}

# ── Ensure .env exists ────────────────────────────────────────────────────────
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host '[docker-up] Created .env from .env.example.'
    Write-Host '[docker-up] Edit .env and set IRONCLAW_AUTH_TOKEN / GATEWAY_AUTH_TOKEN before first use.'
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
    docker compose down -v
}

# ── Build images ──────────────────────────────────────────────────────────────
$buildArgs = @('compose', 'build')
if ($Fresh) {
    Write-Host '[docker-up] Full no-cache rebuild ...'
    $buildArgs += '--no-cache'
} else {
    Write-Host '[docker-up] Building changed images ...'
}
# Build targets in dependency order
$buildArgs += 'openspace-remote-agent', 'openspace-runtime', 'agents-monitor', 'cubecloud-dashboard'
& docker @buildArgs

if (-not $?) {
    Write-Error '[docker-up] docker compose build failed. See output above.'
    exit 1
}

# ── Start / restart containers ────────────────────────────────────────────────
if (-not $Build) {
    Write-Host '[docker-up] Starting containers ...'
    docker compose up -d --remove-orphans

    Write-Host ''
    Write-Host '[docker-up] Stack is up. Service URLs:'
    Write-Host '  Cubecloud dashboard   http://127.0.0.1:7788'
    Write-Host '  Agents monitor        http://127.0.0.1:5173'
    Write-Host '  OpenSpace runtime MCP http://127.0.0.1:8788/mcp'
    Write-Host '  OpenSpace remote MCP  http://127.0.0.1:8789/mcp'
    Write-Host ''
    Write-Host '[docker-up] Tip: run with -Status to check container health.'
} else {
    Write-Host '[docker-up] Build complete. Run "docker compose up -d" to start.'
}
