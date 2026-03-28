param(
    [string]$BundleDir = "",
    [switch]$CopyState
)

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$TemplateDir = Join-Path $RepoRoot 'deploy\local-runtime'

if (-not $BundleDir) {
    $BundleDir = Join-Path (Split-Path -Parent $RepoRoot) 'OpenSpace-runtime'
}

$BundleDir = [System.IO.Path]::GetFullPath($BundleDir)

$bundleConfigDir = Join-Path $BundleDir 'openspace\config'
$bundleStateDir = Join-Path $BundleDir '.openspace'
$bundleLogsDir = Join-Path $BundleDir 'logs'

New-Item -ItemType Directory -Force -Path $BundleDir | Out-Null
New-Item -ItemType Directory -Force -Path $bundleConfigDir | Out-Null
New-Item -ItemType Directory -Force -Path $bundleStateDir | Out-Null
New-Item -ItemType Directory -Force -Path $bundleLogsDir | Out-Null

Copy-Item (Join-Path $TemplateDir 'docker-compose.yml') (Join-Path $BundleDir 'docker-compose.yml') -Force
Copy-Item (Join-Path $TemplateDir 'README.md') (Join-Path $BundleDir 'README.md') -Force
Copy-Item (Join-Path $TemplateDir '.gitignore') (Join-Path $BundleDir '.gitignore') -Force

$rootEnvExample = Join-Path $RepoRoot '.env.example'
if (Test-Path $rootEnvExample) {
    Copy-Item $rootEnvExample (Join-Path $BundleDir '.env.example') -Force
}

$rootEnv = Join-Path $RepoRoot '.env'
if (Test-Path $rootEnv) {
    Copy-Item $rootEnv (Join-Path $BundleDir '.env') -Force
}

Copy-Item (Join-Path $RepoRoot 'openspace\config\external_agents.json') (Join-Path $bundleConfigDir 'external_agents.json') -Force
Copy-Item (Join-Path $RepoRoot 'openspace\config\standalone_apps.json') (Join-Path $bundleConfigDir 'standalone_apps.json') -Force

if ($CopyState) {
    $rootState = Join-Path $RepoRoot '.openspace'
    if (Test-Path $rootState) {
        Copy-Item (Join-Path $rootState '*') $bundleStateDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    $rootLogs = Join-Path $RepoRoot 'logs'
    if (Test-Path $rootLogs) {
        Copy-Item (Join-Path $rootLogs '*') $bundleLogsDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Runtime bundle prepared at: $BundleDir"
Write-Host "Compose file: $(Join-Path $BundleDir 'docker-compose.yml')"

if (Test-Path (Join-Path $BundleDir '.env')) {
    Write-Host 'Copied .env into the runtime bundle.'
}
else {
    Write-Host 'No root .env found. Copy or create one in the runtime bundle before starting containers.'
}

if ($CopyState) {
    Write-Host 'Copied .openspace and logs into the runtime bundle.'
}
else {
    Write-Host 'State directories were created empty. Re-run with -CopyState if you want to carry current .openspace and logs.'
}