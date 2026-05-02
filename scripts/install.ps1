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
    -ImageTag       Pin the GHCR release tag to pull, e.g. v0.6.1.
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
    .\scripts\install.ps1 -InstallPath D:\cubecloud -ImageTag v0.6.1

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

# Optional: OpenClaw URL/token
$openclawUrl = Get-EnvValue 'OPENCLAW_INTERNAL_URL'
if (-not $openclawUrl) {
    Write-Warn "OPENCLAW_INTERNAL_URL not found in .env — OpenClaw defaults will be used (port 18788)."
} else {
    Write-OK "OPENCLAW_INTERNAL_URL: $openclawUrl"
}

$openclawToken = Get-EnvValue 'OPENCLAW_AUTH_TOKEN'
if (-not $openclawToken) {
    Write-Warn "OPENCLAW_AUTH_TOKEN is blank — OpenClaw handoff will not work until it is set."
} else {
    Write-OK "OPENCLAW_AUTH_TOKEN set."
}

$openclawOllamaBaseUrl = Get-EnvValue 'OPENCLAW_OLLAMA_BASE_URL'
if (-not $openclawOllamaBaseUrl) {
    Write-Warn "OPENCLAW_OLLAMA_BASE_URL is blank — OpenClaw will keep its own provider baseUrl. Set this if host.docker.internal:11434 is unreliable from the OpenClaw container."
} else {
    Write-OK "OPENCLAW_OLLAMA_BASE_URL: $openclawOllamaBaseUrl"
}

# Optional: Hermes API key
$hermesKey = Get-EnvValue 'HERMES_API_KEY'
if (-not $hermesKey) {
    Write-Warn "HERMES_API_KEY is blank — Hermes handoff may return 401 until it is set if your gateway requires auth."
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

    function Invoke-JsonRequest {
        param(
            [string]$Method = 'GET',
            [Parameter(Mandatory)]
            [string]$Uri,
            [hashtable]$Headers = @{},
            [object]$Body = $null,
            [int]$TimeoutSec = 30
        )

        Add-Type -AssemblyName System.Net.Http
        $client = [System.Net.Http.HttpClient]::new()
        $client.Timeout = [TimeSpan]::FromSeconds($TimeoutSec)
        $request = $null

        try {
            $request = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::new($Method), $Uri)

            foreach ($key in $Headers.Keys) {
                [void]$request.Headers.TryAddWithoutValidation($key, [string]$Headers[$key])
            }

            if ($null -ne $Body) {
                $jsonBody = if ($Body -is [string]) { [string]$Body } else { $Body | ConvertTo-Json -Depth 10 -Compress }
                $request.Content = [System.Net.Http.StringContent]::new($jsonBody, [System.Text.Encoding]::UTF8, 'application/json')
            }

            $response = $client.SendAsync($request).GetAwaiter().GetResult()
            $content = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()

            return [PSCustomObject]@{
                StatusCode = [int]$response.StatusCode
                IsSuccessStatusCode = $response.IsSuccessStatusCode
                Content = $content
            }
        } finally {
            if ($request) {
                $request.Dispose()
            }
            $client.Dispose()
        }
    }

    function Test-HandoffProbe($label, $agentId, $prompt, $timeoutSec = 90) {
        try {
            $response = Invoke-JsonRequest -Method 'POST' -Uri "http://127.0.0.1:7788/api/v1/external-agents/$agentId/handoff" -Body @{ prompt = $prompt } -TimeoutSec $timeoutSec
            if (-not $response.IsSuccessStatusCode) {
                $details = if ($response.Content) { $response.Content } else { '<no body>' }
                Write-Warn "$label  HTTP $($response.StatusCode) — $details"
                $script:fail++
                return
            }

            $payload = $null
            if ($response.Content) {
                try {
                    $payload = $response.Content | ConvertFrom-Json
                } catch {
                    $payload = $null
                }
            }

            $statusText = if ($payload -and $payload.status) { [string]$payload.status } else { 'ok' }
            $threadSuffix = if ($payload -and $payload.threadId) { "  threadId=$($payload.threadId)" } else { '' }
            $replySuffix = ''
            if ($payload -and $payload.latestTurn -and $payload.latestTurn.response) {
                $replyText = [string]$payload.latestTurn.response
                if ($replyText.Length -gt 40) {
                    $replyText = $replyText.Substring(0, 40) + '...'
                }
                $replySuffix = "  reply=$replyText"
            }

            Write-OK "$label  HTTP $($response.StatusCode)  status=$statusText$threadSuffix$replySuffix"
            $script:pass++
        } catch {
            Write-Warn "$label  FAILED — $_"
            $script:fail++
        }
    }

    Test-Endpoint "Dashboard health"         "http://127.0.0.1:7788/api/v1/health"
    Test-Endpoint "External agents registry" "http://127.0.0.1:7788/api/v1/external-agents"
    Test-Endpoint "Standalone apps registry" "http://127.0.0.1:7788/api/v1/standalone-apps"
    Test-Endpoint "Runtime MCP"              "http://127.0.0.1:8788/mcp"

    if ($ironToken) {
        Test-HandoffProbe "IronClaw handoff" "ironclaw" "Reply with exactly pong" 45
    } else {
        Write-Warn "IronClaw handoff probe skipped — IRONCLAW_AUTH_TOKEN is blank."
    }

    if ($hermesKey) {
        Test-HandoffProbe "Hermes handoff" "hermes" "Reply with exactly pong" 90
    } else {
        Write-Warn "Hermes handoff probe skipped — HERMES_API_KEY is blank."
    }

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
Write-Host "    Remote MCP        internal-only via openspace-remote-agent:8080/mcp" -ForegroundColor White
Write-Host "────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Done. Edit .env to configure agent tokens and URLs." -ForegroundColor Cyan
Write-Host ""
