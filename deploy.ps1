#requires -Version 5.1
<#
.SYNOPSIS
  One-command NutriFlow local deployment.
.DESCRIPTION
  Pulls the configured branch, runs Alembic + additive catalogue patches and
  restarts only affected managed services. Never resets household data.
#>
[CmdletBinding()]
param(
    [string]$Branch = "codex/ux-drawer-next-batch-20261119",
    [string]$PythonPath = "",
    [int]$ApiPort = 8000,
    [int]$WebPort = 5173,
    [switch]$ForceRestart
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$apiDir = Join-Path $root 'apps\api'
$webDir = Join-Path $root 'apps\web'
$stateDir = Join-Path $root '.nutriflow-local'
$stateFile = Join-Path $stateDir 'deployment.json'

function Run([string]$exe,[string[]]$arg,[string]$cwd=$root) {
    Push-Location $cwd
    try {
        & $exe @arg
        if ($LASTEXITCODE -ne 0) { throw ('Command failed: ' + $exe + ' ' + ($arg -join ' ')) }
    } finally { Pop-Location }
}
function Executable([string]$name) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $cmd) { throw ('Missing executable: ' + $name) }
    return $cmd.Source
}
function Listener([int]$port) {
    return @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}
function Healthy([string]$url) {
    try {
        $r = Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 3
        return ([int]$r.StatusCode -ge 200 -and [int]$r.StatusCode -lt 400)
    } catch { return $false }
}
function VerifiedServiceProcess([int]$port,[string]$role) {
    $owners = @(Listener $port | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($owners.Count -eq 0) { return $null }
    if ($owners.Count -ne 1) {
        throw ('Port ' + $port + ' has multiple owners; inspect before restarting.')
    }
    $ownerId = [int]$owners[0]
    $info = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $ownerId)
    if (-not $info -or -not $info.CommandLine) { return $null }
    $line = [string]$info.CommandLine
    $executableName = [IO.Path]::GetFileName([string]$info.ExecutablePath)
    if ($role -eq 'frontend') {
        $vitePath = Join-Path $webDir 'node_modules\vite\bin\vite.js'
        $valid = $executableName -ieq 'node.exe' -and (
            $line.IndexOf($vitePath,[StringComparison]::OrdinalIgnoreCase) -ge 0 -or
            ($line -match 'vite(?:\.js)?(?:\s|["'']|$)' -and
             (Test-Path $vitePath) -and (Healthy ('http://127.0.0.1:' + $port + '/')))
        )
    } else {
        $valid = (
            ($executableName -match '^(python(?:w)?|uvicorn)\.exe$') -and
            ($line -match 'uvicorn|app\.main:app') -and
            (Test-NutriFlowApi $port)
        )
    }
    if (-not $valid) { return $null }
    return Get-Process -Id $ownerId -ErrorAction Stop
}
function Test-NutriFlowApi([int]$port) {
    try {
        $data = Invoke-RestMethod -Uri ('http://127.0.0.1:' + $port + '/openapi.json') -TimeoutSec 3
        return [string]$data.info.title -eq 'NutriFlow AI'
    } catch { return $false }
}
function StateEntry([int]$port,$entry) {
    $listeners = @(Listener $port)
    if ($listeners.Count -eq 0) { return $null }
    if ($null -eq $entry -or -not $entry.pid) {
        return $null
    }
    $process = Get-Process -Id ([int]$entry.pid) -ErrorAction SilentlyContinue
    if (-not $process) { return $null }
    if ($process.StartTime.ToUniversalTime().ToString('o') -ne [string]$entry.start_utc) {
        return $null
    }
    if (@($listeners | Select-Object -ExpandProperty OwningProcess) -notcontains $process.Id) {
        return $null
    }
    return $process
}
function AdoptLegacy([int]$port,[string]$role) {
    if (@(Listener $port).Count -eq 0) { return $null }
    $process = VerifiedServiceProcess $port $role
    if (-not $process) {
        $owners = @(Listener $port | Select-Object -ExpandProperty OwningProcess -Unique)
        foreach ($ownerId in $owners) {
            $info = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $ownerId)
            Write-Warning ('Port ' + $port + ' PID ' + $ownerId +
                ' is not verified as NutriFlow; executable=' + $info.ExecutablePath +
                '; command=' + $info.CommandLine)
        }
        throw ('Cannot safely adopt process on port ' + $port + '. No process was terminated.')
    }
    Write-Host ('Found NutriFlow ' + $role + ' listener PID ' + $process.Id)
    $answer = Read-Host 'Authorize taking over this service? Type SIM'
    if ($answer -cne 'SIM') { throw ('Takeover of ' + $role + ' not authorized.') }
    return @{ pid=$process.Id; start_utc=$process.StartTime.ToUniversalTime().ToString('o') }
}
function StopManaged([int]$port,$entry) {
    $process = StateEntry $port $entry
    if ($null -eq $process) { return }
    Write-Host ('Stopping managed PID ' + $process.Id + ' on port ' + $port)
    Stop-Process -Id $process.Id
    try { Wait-Process -Id $process.Id -Timeout 15 -ErrorAction Stop }
    catch {
        if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) { throw }
    }
    if (@(Listener $port).Count) { throw ('Port still occupied after stop: ' + $port) }
}
function Launch([string]$exe,[string[]]$arg,[string]$cwd,[string]$name,[int]$port,[string]$url) {
    if (@(Listener $port).Count) { throw ('Port already occupied: ' + $port) }
    $prefix = Join-Path $stateDir $name
    $args = @{
        FilePath = $exe; ArgumentList = $arg; WorkingDirectory = $cwd
        PassThru = $true; WindowStyle = 'Hidden'
        RedirectStandardOutput = ($prefix + '.out.log')
        RedirectStandardError = ($prefix + '.err.log')
    }
    $started = Start-Process @args
    try {
        $ready = $false
        for ($i=0; $i -lt 50; $i++) {
            if (Healthy $url) { $ready = $true; break }
            Start-Sleep -Milliseconds 400
        }
        if (-not $ready) { throw ($name + ' failed health check. See ' + $prefix + '.err.log') }
        # Verify the process that owns the listening socket, not Start-Process's
        # initial PID. On Windows Node/Vite may spawn or hand off to another PID.
        $role = if ($name -eq 'frontend') { 'frontend' } else { 'api' }
        $proc = VerifiedServiceProcess $port $role
        if (-not $proc) {
            throw ($name + ' responded but its listening process is not verified as NutriFlow.')
        }
        Write-Host ($name + ' ready; listener PID ' + $proc.Id)
        return @{ pid=$proc.Id; start_utc=$proc.StartTime.ToUniversalTime().ToString('o') }
    } catch {
        Stop-Process -Id $started.Id -ErrorAction SilentlyContinue
        throw
    }
}
function Save($state) {
    $state | ConvertTo-Json -Depth 6 | Set-Content -Path $stateFile -Encoding UTF8
}
if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir | Out-Null }
$git = Executable 'git'
$node = Executable 'node'
$docker = Executable 'docker'
if (-not $PythonPath) {
    $choices = @((Join-Path $root '.venv\Scripts\python.exe'),(Join-Path $apiDir '.venv\Scripts\python.exe'))
    foreach ($candidate in $choices) {
        if (Test-Path $candidate) { $PythonPath = $candidate; break }
    }
    if (-not $PythonPath) { $PythonPath = Executable 'python' }
}
if (-not (Test-Path $PythonPath) -and -not (Get-Command $PythonPath -ErrorAction SilentlyContinue)) {
    throw ('Python not found: ' + $PythonPath)
}
$repoRoot = (& $git -C $root rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or (Resolve-Path $repoRoot).Path -ne (Resolve-Path $root).Path) {
    throw 'deploy.ps1 must be placed at the repository root.'
}
$branchNow = (& $git -C $root branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $branchNow -ne $Branch) {
    throw ('Expected branch ' + $Branch + ', found ' + $branchNow)
}
$dirty = @(& $git -C $root status --porcelain)
if ($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0) {
    throw ('Working tree is not clean. Commit or stash first: ' + ($dirty -join '; '))
}
$previous = $null
if (Test-Path $stateFile) { $previous = Get-Content $stateFile -Raw | ConvertFrom-Json }
if ($previous -and [string]$previous.root -ne $root) { throw 'State belongs to a different checkout.' }
$oldApi = if ($previous) { $previous.api } else { $null }
$oldWeb = if ($previous) { $previous.web } else { $null }
# Verify saved PIDs first. A stale PID must not stop another process.
$apiRunning = StateEntry $ApiPort $oldApi
$webRunning = StateEntry $WebPort $oldWeb
$adoptedApi = $false
$adoptedWeb = $false
if (-not $apiRunning -and @(Listener $ApiPort).Count -gt 0) {
    $oldApi = AdoptLegacy $ApiPort 'api'
    $adoptedApi = $true
    $apiRunning = StateEntry $ApiPort $oldApi
}
if (-not $webRunning -and @(Listener $WebPort).Count -gt 0) {
    $oldWeb = AdoptLegacy $WebPort 'frontend'
    $adoptedWeb = $true
    $webRunning = StateEntry $WebPort $oldWeb
}
$before = (& $git -C $root rev-parse HEAD).Trim()
Write-Host ('Fetching and pulling ' + $Branch)
Run $git @('-C',$root,'fetch','origin',$Branch)
Run $git @('-C',$root,'pull','--ff-only','origin',$Branch)
$after = (& $git -C $root rev-parse HEAD).Trim()
# Keep this as an actual array even when no files changed.
# PowerShell's expression assignment collapses an empty @() to $null.
$changed = @()
if ($before -ne $after) {
    $changed = @(& $git -C $root diff --name-only $before $after)
    if ($LASTEXITCODE -ne 0) { throw 'git diff failed after updating the repository.' }
}
$apiChanged = $ForceRestart -or $adoptedApi -or -not $apiRunning -or
    @($changed | Where-Object { $_ -match '^(apps/api/|database/|alembic\.ini$|compose\.yml$|deploy\.ps1$)' }).Count -gt 0
$webChanged = $ForceRestart -or $adoptedWeb -or -not $webRunning -or
    @($changed | Where-Object { $_ -match '^(apps/web/|packages/|deploy\.ps1$)' }).Count -gt 0
Write-Host ('Updated to ' + $after + '; files changed: ' + $changed.Count)
$state = @{ root=$root; revision=$after; api=$oldApi; web=$oldWeb }
Run $docker @('compose','-f',(Join-Path $root 'compose.yml'),'up','-d','--wait','db')
if ($apiChanged) {
    if ($apiChanged -and $oldApi) {
        StopManaged $ApiPort $oldApi
        $state.api = $null
        Save $state
    }
    if (@($changed | Where-Object { $_ -match '^apps/api/pyproject\.toml$' }).Count -gt 0) {
        Write-Host 'Refreshing API dependencies after manifest changes...'
        Run $PythonPath @('-m','pip','install','-e',(Join-Path $root 'apps/api')) $root
    }
    Write-Host 'Applying Alembic and reference catalogue updates...'
    Run $PythonPath @('-m','app.local_db_update') $apiDir
}
if ($webChanged) {
    if ($oldWeb) {
        StopManaged $WebPort $oldWeb
        $state.web = $null
        Save $state
    }
    $vite = Join-Path $webDir 'node_modules\vite\bin\vite.js'
    if (@($changed | Where-Object { $_ -match '^apps/web/package(-lock)?\.json$' }).Count -gt 0) {
        $npm = Executable 'npm.cmd'
        Write-Host 'Refreshing frontend dependencies after manifest changes...'
        Run $npm @('install','--no-package-lock','--ignore-scripts') $webDir
    }
    if (-not (Test-Path $vite)) {
        $npm = Executable 'npm.cmd'
        Write-Host 'Installing missing frontend dependencies...'
        Run $npm @('install','--no-package-lock','--ignore-scripts') $webDir
    }
    if (-not (Test-Path $vite)) { throw 'Vite was not installed.' }
    $state.web = Launch $node @($vite,'--host','127.0.0.1','--port',"$WebPort",'--strictPort') $webDir 'frontend' $WebPort ('http://127.0.0.1:' + $WebPort + '/')
    Save $state
}
if ($apiChanged) {
    $state.api = Launch $PythonPath @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$ApiPort") $apiDir 'api' $ApiPort ('http://127.0.0.1:' + $ApiPort + '/openapi.json')
    Save $state
}
if (-not (Healthy ('http://127.0.0.1:' + $ApiPort + '/openapi.json')) -or
    -not (Healthy ('http://127.0.0.1:' + $WebPort + '/'))) {
    throw 'Final API/web health checks failed.'
}
Write-Host ('Deployment successful: ' + $after)
Write-Host ('Open http://127.0.0.1:' + $WebPort + '/')
