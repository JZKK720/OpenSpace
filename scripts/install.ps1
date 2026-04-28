<#
.SYNOPSIS
    One-shot install script for the OpenSpace Cubecloud fork on Windows.

.DESCRIPTION
    Clones (or updates) the fork, sets up .env, and starts the Docker stack.
    Run this on any Windows machine with Git and Docker Desktop installed.

    Usage (fresh machine):
        irm https://raw.githubusercontent.com/JZKK720/OpenSpace/main/scripts/install.ps1 | iex

    Or from a local clone:
        .\scripts\install.ps1

    Options
    --------
    -InstallPath    Where to clone the repo.  Default: C:\OpenSpace
    -Branch         Branch to track.          Default: main
    -SkipDocker     Set up files only; skip docker compose up.
    -LocalBuild     Use local Docker builds instead of GHCR release images.
    -ImageTag       Pin the GHCR release tag to pull, e.g. v0.5.0.
    -Fresh          Pass -Fresh to docker-up (full no-cache rebuild, requires -LocalBuild).
    -Down           Pass -Down to docker-up  (wipe containers first).

.PARAMETER InstallPath
    Destination folder for the clone.  Ignored if already inside the repo.

.PARAMETER Branch
    Git branch to check out.  Default: main.

.PARAMETER SkipDocker
    Only clone/configure files; do not start the Docker stack.

.PARAMETER LocalBuild
    Use the checked-in Dockerfiles and local compose file instead of GHCR images.

.PARAMETER ImageTag
    Persist OPENSPACE_IMAGE_TAG in .env before starting the stack.

.PARAMETER Fresh
    Force a full no-cache Docker image rebuild. Requires -LocalBuild.

.PARAMETER Down
    Stop and remove containers before rebuilding.

.EXAMPLE
    # Minimal GHCR-based install (will prompt for tokens):
    .\scripts\install.ps1

    # Install to a custom path and pin a tagged release:
    .\scripts\install.ps1 -InstallPath D:\cubecloud -ImageTag v0.5.0

    # Local-build fallback (rebuild images from source):
    .\scripts\install.ps1 -LocalBuild -Fresh
#>
param(
    [string]$InstallPath = 'C:\OpenSpace',
    [string]$Branch      = 'main',
    [switch]$SkipDocker,
    [switch]$LocalBuild,
    [string]$ImageTag = '',
    [switch]$Fresh,
    [switch]$Down
)

$ErrorActionPreference = 'Stop'
$ForkUrl = 'https://github.com/JZKK720/OpenSpace.git'

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
function Check-Command($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Error "[install] '$name' is not installed or not on PATH. Please install it and retry."
        exit 1
    }
}

function Write-Step($msg) { Write-Host "`n[install] $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "  OK  $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  WARN $msg" -ForegroundColor Yellow }

# ─────────────────────────────────────────────────────────────────────────────
# 1. Pre-flight checks
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Pre-flight checks"
Check-Command git
Check-Command docker

if ($Fresh -and -not $LocalBuild) {
    Write-Error '[install] -Fresh requires -LocalBuild. The default install path pulls GHCR images.'
    exit 1
}

# Verify Docker daemon is running
try {
    docker info 2>&1 | Out-Null
    Write-OK "Docker daemon is running."
} catch {
    Write-Error "[install] Docker is not running. Start Docker Desktop and retry."
    exit 1
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Clone or update
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Repository setup"

# If we're already inside a clone, use that as the repo root
$insideClone = $false
try {
    $toplevel = git -C $PSScriptRoot rev-parse --show-toplevel 2>$null
    if ($toplevel) {
        $RepoRoot = $toplevel.Trim()
        $insideClone = $true
        Write-OK "Already inside clone at '$RepoRoot' — skipping clone step."
    }
} catch {}

if (-not $insideClone) {
    if (Test-Path (Join-Path $InstallPath '.git')) {
        Write-OK "Existing clone found at '$InstallPath' — pulling latest."
        $RepoRoot = $InstallPath
        Push-Location $RepoRoot
        $dirty = git status --porcelain
        if ($dirty) {
            Write-Warn "Working tree is dirty — skipping pull. Commit or stash changes manually."
        } else {
            git fetch origin --tags
            git checkout $Branch
            git pull --ff-only origin $Branch
            Write-OK "Pulled latest from origin/$Branch."
        }
        Pop-Location
    } else {
        Write-OK "Cloning fork into '$InstallPath' ..."
        git clone --branch $Branch $ForkUrl $InstallPath
        $RepoRoot = $InstallPath
        Write-OK "Clone complete."
    }
}

Set-Location $RepoRoot

# ─────────────────────────────────────────────────────────────────────────────
# 3. .env setup
# ─────────────────────────────────────────────────────────────────────────────
Write-Step ".env configuration"

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-OK "Created .env from .env.example."
} else {
    Write-OK ".env already exists — keeping existing values."
}

if ($ImageTag) {
    Set-EnvValue 'OPENSPACE_IMAGE_TAG' $ImageTag
    Write-OK "OPENSPACE_IMAGE_TAG pinned to $ImageTag."
} else {
    $currentImageTag = Get-EnvValue 'OPENSPACE_IMAGE_TAG'
    if ($currentImageTag) {
        Write-OK "OPENSPACE_IMAGE_TAG: $currentImageTag"
    }
}

# Helper: read current value from .env
function Get-EnvValue($key) {
    $line = Select-String -Path '.env' -Pattern "^$key=" | Select-Object -First 1
    if ($line) { return ($line.Line -split '=', 2)[1] }
    return $null
}

# Helper: write or update a key=value in .env
function Set-EnvValue($key, $value) {
    $content = Get-Content '.env' -Raw
    if ($content -match "(?m)^$key=") {
        $content = $content -replace "(?m)^$key=.*", "$key=$value"
    } else {
        $content = $content.TrimEnd() + "`n$key=$value`n"
    }
    Set-Content '.env' $content -NoNewline
}

# Prompt for IRONCLAW_AUTH_TOKEN if blank
$ironToken = Get-EnvValue 'IRONCLAW_AUTH_TOKEN'
if (-not $ironToken) {
    Write-Host ""
    Write-Host "  IronClaw gateway token is required for agent handoff." -ForegroundColor Yellow
    $ironToken = Read-Host "  Enter IRONCLAW_AUTH_TOKEN (leave blank to skip)"
    if ($ironToken) {
        Set-EnvValue 'IRONCLAW_AUTH_TOKEN' $ironToken
        Set-EnvValue 'GATEWAY_AUTH_TOKEN'  $ironToken
        Write-OK "IRONCLAW_AUTH_TOKEN set."
    } else {
        Write-Warn "IRONCLAW_AUTH_TOKEN left blank — IronClaw handoff will not work until it is set."
    }
} else {
    Write-OK "IRONCLAW_AUTH_TOKEN already set."
}

# Optional: Nanobot URL (only prompt if user wants to override)
$nanobotUrl = Get-EnvValue 'NANOBOT_INTERNAL_URL'
if (-not $nanobotUrl) {
    Write-Warn "NANOBOT_INTERNAL_URL not found in .env — Nanobot defaults will be used (port 18790)."
} else {
    Write-OK "NANOBOT_INTERNAL_URL: $nanobotUrl"
}

# Optional: Hermes API key
$hermesKey = Get-EnvValue 'HERMES_API_KEY'
if (-not $hermesKey) {
    Write-Warn "HERMES_API_KEY is blank — Hermes agent will be available without API key (local-only mode)."
} else {
    Write-OK "HERMES_API_KEY set."
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Docker stack
# ─────────────────────────────────────────────────────────────────────────────
if ($SkipDocker) {
    Write-Step "Skipping Docker stack (-SkipDocker specified)."
    if ($LocalBuild) {
        Write-Host "`n  When ready, run:  .\scripts\docker-up.ps1 -LocalBuild" -ForegroundColor Cyan
    } else {
        Write-Host "`n  When ready, run:  .\scripts\docker-up.ps1" -ForegroundColor Cyan
    }
} else {
    if ($LocalBuild) {
        Write-Step "Starting Docker stack from local images ..."
    } else {
        Write-Step "Starting Docker stack from GHCR images ..."
    }
    $dockerArgs = @()
    if ($LocalBuild) { $dockerArgs += '-LocalBuild' }
    if ($Fresh) { $dockerArgs += '-Fresh' }
    if ($Down)  { $dockerArgs += '-Down' }
    if ($ImageTag) { $dockerArgs += @('-ImageTag', $ImageTag) }

    & "$RepoRoot\scripts\docker-up.ps1" @dockerArgs

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Smoke verification
    # ─────────────────────────────────────────────────────────────────────────
    Write-Step "Smoke verification (waiting 8s for containers to settle ...)"
    Start-Sleep -Seconds 8

    $pass = 0; $fail = 0

    function Test-Endpoint($label, $url) {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 6 -ErrorAction Stop
            Write-OK "$label  HTTP $($r.StatusCode)"
            $script:pass++
        } catch {
            Write-Warn "$label  UNREACHABLE — $_"
            $script:fail++
        }
    }

    Test-Endpoint "Dashboard health"         "http://127.0.0.1:7788/api/v1/health"
    Test-Endpoint "External agents registry" "http://127.0.0.1:7788/api/v1/external-agents"
    Test-Endpoint "Standalone apps registry" "http://127.0.0.1:7788/api/v1/standalone-apps"
    Test-Endpoint "Runtime MCP"              "http://127.0.0.1:8788/mcp"

    Write-Host ""
    if ($fail -eq 0) {
        Write-Host "  All $pass checks passed." -ForegroundColor Green
    } else {
        Write-Warn "$fail of $($pass + $fail) checks failed. Check 'docker compose logs' for details."
    }
}

Write-Host ""
Write-Host "────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Service URLs" -ForegroundColor White
Write-Host "    Dashboard         http://127.0.0.1:7788" -ForegroundColor White
Write-Host "    Agents monitor    http://127.0.0.1:5173" -ForegroundColor White
Write-Host "    Runtime MCP       http://127.0.0.1:8788/mcp" -ForegroundColor White
Write-Host "    Remote MCP        http://127.0.0.1:8789/mcp" -ForegroundColor White
Write-Host "────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Done. Edit .env to configure agent tokens and URLs." -ForegroundColor Cyan
Write-Host ""
