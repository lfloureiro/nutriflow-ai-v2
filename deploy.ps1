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
    [switch]$ForceRestart,
    [switch]$VerifyFrontendOnly,
    [switch]$VerifyNetstatOnly,
    [switch]$Diagnose
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
    # Query both Windows TCP sources. Get-NetTCPConnection may transiently
    # return zero rows while an existing Uvicorn process is responding.
    $entries = @()
    if (-not ($VerifyFrontendOnly -and $VerifyNetstatOnly)) {
        try {
            $entries = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
                ForEach-Object {
                    [pscustomobject]@{
                        LocalAddress = [string]$_.LocalAddress
                        LocalPort = [int]$_.LocalPort
                        OwningProcess = [int]$_.OwningProcess
                    }
                })
        } catch { $entries = @() }
    }
    foreach ($line in @(& netstat.exe -ano -p tcp 2>$null)) {
        # A listening socket has remote port 0. No locale-specific state
        # comparison is needed to extract the owning PID.
        if ($line -notmatch '^\s*TCP\s+(\S+):(\d+)\s+(\S+):(\d+)\s+\S+\s+(\d+)\s*$') {
            continue
        }
        $localPort = [int]$Matches[2]
        $remotePort = [int]$Matches[4]
        $ownerId = [int]$Matches[5]
        if ($localPort -ne $port -or $remotePort -ne 0 -or $ownerId -le 0) { continue }
        $localAddress = [string]$Matches[1]
        if (@($entries | Where-Object {
            $_.OwningProcess -eq $ownerId -and $_.LocalAddress -eq $localAddress
        }).Count -eq 0) {
            $entries += [pscustomobject]@{
                LocalAddress = $localAddress
                LocalPort = $port
                OwningProcess = $ownerId
            }
        }
    }
    return $entries
}
function Healthy([string]$url) {
    try {
        $r = Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 3
        return ([int]$r.StatusCode -ge 200 -and [int]$r.StatusCode -lt 400)
    } catch { return $false }
}
function Test-NutriFlowFrontend([int]$port) {
    try {
        $baseUrl = 'http://127.0.0.1:' + $port
        $page = Invoke-WebRequest -Uri ($baseUrl + '/') -UseBasicParsing -TimeoutSec 3
        if ([int]$page.StatusCode -ne 200 -or
            [string]$page.Content -notmatch '<title>NutriFlow AI</title>') {
            return $false
        }
        # A regular website with the same title is not proof of a Vite dev server.
        $client = Invoke-WebRequest -Uri ($baseUrl + '/@vite/client') -UseBasicParsing -TimeoutSec 3
        return [int]$client.StatusCode -eq 200 -and
            [string]$client.Content -match 'vite'
    } catch { return $false }
}
function Show-PortDiagnostics([int]$port,[string]$role) {
    Write-Host ('--- NutriFlow ' + $role + ' port ' + $port + ' diagnostics ---')
    $connections = @(Listener $port)
    Write-Host ('TCP listeners: ' + $connections.Count)
    foreach ($connection in $connections) {
        $ownerId = [int]$connection.OwningProcess
        Write-Host ('TCP: ' + $connection.LocalAddress + ':' + $connection.LocalPort +
            ' PID=' + $ownerId)
        $process = Get-Process -Id $ownerId -ErrorAction SilentlyContinue
        $cim = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $ownerId) -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host ('Process: ' + $process.ProcessName + ' PID=' + $process.Id +
                ' StartUTC=' + $process.StartTime.ToUniversalTime().ToString('o'))
        }
        if ($cim) {
            Write-Host ('Executable: ' + [string]$cim.ExecutablePath)
            # Do not print full arguments: applications can contain credentials.
            $line = [string]$cim.CommandLine
            Write-Host ('CommandPrefix: ' + $line.Substring(0,[Math]::Min(180,$line.Length)))
        }
    }
    if ($role -eq 'frontend') {
        Write-Host ('Homepage healthy: ' + (Healthy ('http://127.0.0.1:' + $port + '/')))
        Write-Host ('NutriFlow Vite signature: ' + (Test-NutriFlowFrontend $port))
    } else {
        Write-Host ('NutriFlow API signature: ' + (Test-NutriFlowApi $port))
    }
    Write-Host '--- end diagnostics ---'
}
function VerifiedServiceProcess([int]$port,[string]$role) {
    $owners = @(Listener $port | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($owners.Count -eq 0) { return $null }
    if ($owners.Count -ne 1) {
        throw ('Port ' + $port + ' has multiple owners; inspect before restarting.')
    }
    $ownerId = [int]$owners[0]
    $info = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $ownerId)
    $proc = Get-Process -Id $ownerId -ErrorAction SilentlyContinue
    if (-not $info -or -not $proc) {
        Write-Warning ('Process identification incomplete on port ' + $port +
            '; owner=' + $ownerId)
        return $null
    }
    $line = [string]$info.CommandLine
    $executableName = [IO.Path]::GetFileName([string]$info.ExecutablePath)
    if (-not $executableName) { $executableName = [string]$proc.ProcessName + '.exe' }
    if ($role -eq 'frontend') {
        # Node/Vite may spawn another process, use a relative entrypoint, or
        # hide its command line in Windows CIM. The listening process must
        # actually be Node and respond with the NutriFlow Vite signature.
        $valid = $executableName -ieq 'node.exe' -and
            (Test-NutriFlowFrontend $port)
    } else {
        # --reload can delegate the listener to a Python child with a
        # generic command line. Verify the app's OpenAPI identity instead.
        $valid = ($executableName -match '^(python(?:w)?|uvicorn)\\.exe$') -and
            (Test-NutriFlowApi $port)
    }
    if (-not $valid) {
        Write-Warning ('Process verification rejected port ' + $port +
            ', role=' + $role + ', owner=' + $ownerId +
            ', exe=' + $executableName +
            ', command=' + $line.Substring(0,[Math]::Min(250,$line.Length)) +
            ', NutriFlowVite=' + (Test-NutriFlowFrontend $port))
        return $null
    }
    return $proc
}
function Test-NutriFlowApi([int]$port) {
    try {
        $data = Invoke-RestMethod -Uri ('http://127.0.0.1:' + $port + '/openapi.json') -TimeoutSec 3
        return [string]$data.info.title -eq 'NutriFlow AI'
    } catch { return $false }
}
function FindLocalApiProcess([int]$port,[bool]$AllowSelection = $false) {
    # Never infer the active API from process count alone: old deployments
    # can leave several Uvicorn processes with identical command lines.
    if (-not (Test-NutriFlowApi $port)) { return $null }
    $expectedEnvironment = Join-Path $root '.venv\Scripts\python.exe'
    $candidateProcesses = @()
    foreach ($candidate in @(Get-CimInstance Win32_Process -ErrorAction Stop)) {
        $command = [string]$candidate.CommandLine
        if (-not $command) { continue }
        $normalized = $command.Replace('/', '\')
        if ($normalized.IndexOf($expectedEnvironment,
                [StringComparison]::OrdinalIgnoreCase) -lt 0) { continue }
        if ($normalized -notmatch 'uvicorn\s+app\.main:app') { continue }
        if ($normalized -notmatch ('--port\s+' + $port + '(?:\s|$)')) { continue }
        $process = Get-Process -Id ([int]$candidate.ProcessId) -ErrorAction SilentlyContinue
        if ($process -and $process.ProcessName -match '^python') {
            $candidateProcesses += $process
        }
    }
    if ($candidateProcesses.Count -eq 0) { return $null }

    # The TCP socket owner takes precedence only when exactly one matching
    # candidate owns the port. Never select by process age or list order.
    $owners = @(Listener $port | Select-Object -ExpandProperty OwningProcess -Unique)
    $socketMatches = @($candidateProcesses | Where-Object { $owners -contains $_.Id })
    if ($socketMatches.Count -eq 1) {
        Write-Host ('Verified Uvicorn socket owner on port ' + $port +
            ': PID ' + $socketMatches[0].Id)
        return $socketMatches[0]
    }

    if ($candidateProcesses.Count -eq 1) { return $candidateProcesses[0] }
    Write-Warning ('Found ' + $candidateProcesses.Count +
        ' matching local NutriFlow Uvicorn processes on port ' + $port +
        '; TCP owners found: ' + ($owners -join ', '))
    foreach ($process in $candidateProcesses) {
        $isListener = if ($owners -contains $process.Id) { ' [TCP OWNER]' } else { '' }
        Write-Host ('Candidate PID ' + $process.Id +
            ', start UTC ' + $process.StartTime.ToUniversalTime().ToString('o') +
            $isListener)
    }
    if (-not $AllowSelection) { return $null }
    # Explicit selection is a recovery action, never an automatic kill.
    # AdoptLegacy will independently request confirmation before stopping.
    $chosen = Read-Host ('Select the PID to adopt for port ' + $port +
        ' (or press Enter to cancel)')
    if ($chosen -notmatch '^\d+$') { throw 'No valid API PID selected. No process terminated.' }
    $picked = @($candidateProcesses | Where-Object { $_.Id -eq [int]$chosen })
    if ($picked.Count -ne 1) {
        throw ('PID ' + $chosen + ' is not one of the verified NutriFlow candidates.')
    }
    return $picked[0]
}
function TestLocalApiPid([int]$port,[int]$processId) {
    if (-not (Test-NutriFlowApi $port)) { return $false }
    $info = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $processId) -ErrorAction SilentlyContinue
    if (-not $info -or -not $info.CommandLine) { return $false }
    $command = ([string]$info.CommandLine).Replace('/', '\')
    $expectedEnvironment = Join-Path $root '.venv\Scripts\python.exe'
    return (
        $command.IndexOf($expectedEnvironment,
            [StringComparison]::OrdinalIgnoreCase) -ge 0 -and
        $command -match 'uvicorn\s+app\.main:app' -and
        $command -match ('--port\s+' + $port + '(?:\s|$)')
    )
}
function IsTrustedLaunch($entry) {
    if ($null -eq $entry) { return $false }
    if ($entry -is [System.Collections.IDictionary]) {
        return $entry.Contains('trusted_launch') -and [bool]$entry['trusted_launch']
    }
    $property = $entry.PSObject.Properties['trusted_launch']
    return $null -ne $property -and [bool]$property.Value
}
function StateEntry([int]$port,$entry) {
    $listeners = @(Listener $port)
    if ($null -eq $entry -or -not $entry.pid) {
        return $null
    }
    $process = Get-Process -Id ([int]$entry.pid) -ErrorAction SilentlyContinue
    if (-not $process) { return $null }
    if ($process.StartTime.ToUniversalTime().ToString('o') -ne [string]$entry.start_utc) {
        return $null
    }
    if (@($listeners | Select-Object -ExpandProperty OwningProcess) -notcontains $process.Id) {
        # Legacy API: accept the exact saved PID only if the matching local
        # Uvicorn command and NutriFlow OpenAPI response still agree.
        if ($process.ProcessName -match '^python' -and
            (TestLocalApiPid $port $process.Id)) {
            return $process
        }
        # The Vite PID was recorded by this deploy script immediately after
        # starting Node on a previously free port; some Windows configurations
        # report a different TCP owner. Never apply this to adopted processes.
        if (-not (IsTrustedLaunch $entry) -or
            $process.ProcessName -ine 'node' -or
            -not (Healthy ('http://127.0.0.1:' + $port + '/'))) {
            return $null
        }
    }
    return $process
}
function AdoptLegacy([int]$port,[string]$role) {
    $hasListeners = @(Listener $port).Count -gt 0
    $hasHttp = if ($role -eq 'api') {
        Test-NutriFlowApi $port
    } else {
        Test-NutriFlowFrontend $port
    }
    if (-not $hasListeners -and -not $hasHttp) { return $null }
    $process = VerifiedServiceProcess $port $role
    if (-not $process -and $role -eq 'api') {
        $process = FindLocalApiProcess $port $true
    }
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
    if (@(Listener $port).Count -gt 0 -or
        (Healthy ('http://127.0.0.1:' + $port + '/'))) {
        throw ('Port ' + $port + ' still responds or is occupied after stopping PID ' +
            $process.Id + '. Refusing to start a second server.')
    }
}
function Launch([string]$exe,[string[]]$arg,[string]$cwd,[string]$name,[int]$port,[string]$url) {
    if (@(Listener $port).Count -gt 0 -or (Healthy $url)) {
        throw ('Port ' + $port + ' already responds or has a listener. Refusing second ' + $name)
    }
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
        $role = if ($name -like 'frontend*') { 'frontend' } else { 'api' }
        $proc = VerifiedServiceProcess $port $role
        if (-not $proc -and $role -eq 'frontend') {
            # Fresh startup had a free port, then this script launched the
            # expected Vite executable and verified the HTTP response. Windows
            # can report an altered Vite HTML/command-line fingerprint; in
            # that case verify the *new* Node socket owner against launch time.
            # Do not use this fallback when adopting an existing process.
            $launchProc = Get-Process -Id $started.Id -ErrorAction SilentlyContinue
            $expectedVite = Join-Path $webDir 'node_modules\vite\bin\vite.js'
            $isViteLaunch = $exe -ieq (Executable 'node') -and
                ($arg.Count -gt 0) -and
                ([string]$arg[0] -ieq $expectedVite)
            # The CI fixture deliberately omits the Vite fingerprint, so the
            # fallback is actually exercised on a real Windows TCP listener.
            if ($VerifyFrontendOnly -and $name -eq 'frontend-test' -and
                $arg.Count -gt 0 -and
                ([string]$arg[0] -ieq (Join-Path $root 'tools\deploy-smoke-server.cjs'))) {
                $isViteLaunch = $true
            }
            if ($launchProc -and $isViteLaunch) {
                $candidates = @(Listener $port | Select-Object -ExpandProperty OwningProcess -Unique)
                if ($candidates.Count -eq 1) {
                    $socketProc = Get-Process -Id ([int]$candidates[0]) -ErrorAction SilentlyContinue
                    if ($socketProc -and $socketProc.ProcessName -ieq 'node' -and
                        $socketProc.StartTime -ge $started.StartTime -and (Healthy $url)) {
                        $proc = $socketProc
                        Write-Warning ('Accepted newly started Vite Node listener PID ' +
                            $proc.Id + ' using launch-time ownership verification.')
                    }
                }
            }
        }
        $trustedLaunch = $false
        if (-not $proc -and $role -eq 'frontend') {
            # Strong fallback: we observed a free port, launched a specific
            # local Vite Node process and then got a healthy response. Check
            # that exact process still exists before managing its PID.
            $direct = Get-Process -Id $started.Id -ErrorAction SilentlyContinue
            $knownVite = Join-Path $webDir 'node_modules\vite\bin\vite.js'
            $knownFixture = Join-Path $root 'tools\deploy-smoke-server.cjs'
            $expectedScript = if ($VerifyFrontendOnly -and $name -eq 'frontend-test') {
                $knownFixture
            } else {
                $knownVite
            }
            if ($direct -and $direct.ProcessName -ieq 'node' -and
                $exe -ieq (Executable 'node') -and
                $arg.Count -gt 0 -and
                [string]$arg[0] -ieq $expectedScript -and
                (Healthy $url)) {
                $proc = $direct
                $trustedLaunch = $true
                Write-Warning ('Using directly launched Node PID ' + $proc.Id +
                    ' because Windows TCP ownership verification was inconclusive.')
            }
        }
        if (-not $proc) {
            Show-PortDiagnostics $port $role
            Write-Host ('Launch PID: ' + $started.Id + '; running: ' +
                [bool](Get-Process -Id $started.Id -ErrorAction SilentlyContinue))
            Write-Host ('Launch executable: ' + $exe)
            Write-Host ('Launch first argument: ' + $(if ($arg.Count -gt 0) { $arg[0] } else { '' }))
            throw ($name + ' responded but its listening process is not verified as NutriFlow. ' +
                'Inspect the diagnostics above and ' + (Join-Path $stateDir ($name + '.err.log')))
        }
        Write-Host ($name + ' ready; managed PID ' + $proc.Id)
        return @{
            pid=$proc.Id
            start_utc=$proc.StartTime.ToUniversalTime().ToString('o')
            trusted_launch=$trustedLaunch
        }
    } catch {
        Stop-Process -Id $started.Id -ErrorAction SilentlyContinue
        throw
    }
}
function Save($state) {
    $state | ConvertTo-Json -Depth 6 | Set-Content -Path $stateFile -Encoding UTF8
}
if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir | Out-Null }
if ($Diagnose) {
    Show-PortDiagnostics $ApiPort 'api'
    Show-PortDiagnostics $WebPort 'frontend'
    if (Test-Path $stateFile) {
        $previousState = Get-Content $stateFile -Raw | ConvertFrom-Json
        foreach ($kind in @('api','web')) {
            $saved = $previousState.$kind
            if ($saved) { Write-Host ('Tracked ' + $kind + ' PID: ' + $saved.pid) }
        }
    }
    exit 0
}
if ($VerifyFrontendOnly) {
    # Windows CI smoke test of the actual launch/port ownership implementation.
    # Uses a zero-dependency HTTP signature fixture; Web CI tests real Vite.
    # This never pulls code, touches Docker or changes a database.
    $nodeForTest = Executable 'node'
    $fixtureForTest = Join-Path $root 'tools\deploy-smoke-server.cjs'
    if (-not (Test-Path $fixtureForTest)) { throw 'Missing Windows HTTP smoke fixture.' }
    $entry = Launch $nodeForTest @($fixtureForTest,"$WebPort") $root 'frontend-test' $WebPort ('http://127.0.0.1:' + $WebPort + '/')
    try {
        $verified = StateEntry $WebPort $entry
        if (-not $verified) { throw 'The verified frontend process was not tracked.' }
        Write-Host ('Windows Vite launch and ownership smoke test passed, PID ' + $verified.Id)
    } finally {
        StopManaged $WebPort $entry
    }
    exit 0
}
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
if (-not $apiRunning -and (
    @(Listener $ApiPort).Count -gt 0 -or (Test-NutriFlowApi $ApiPort)
)) {
    $oldApi = AdoptLegacy $ApiPort 'api'
    $adoptedApi = $true
    $apiRunning = StateEntry $ApiPort $oldApi
}
if (-not $webRunning -and (
    @(Listener $WebPort).Count -gt 0 -or (Test-NutriFlowFrontend $WebPort)
)) {
    $oldWeb = AdoptLegacy $WebPort 'frontend'
    $adoptedWeb = $true
    $webRunning = StateEntry $WebPort $oldWeb
}
# A responding port is not free just because one Windows TCP query
# reports no rows. Abort rather than starting duplicate API/Vite processes.
if (-not $apiRunning -and @(Listener $ApiPort).Count -eq 0 -and
    (Healthy ('http://127.0.0.1:' + $ApiPort + '/openapi.json'))) {
    Show-PortDiagnostics $ApiPort 'api'
    throw 'API already responds but TCP owner could not be established; refusing second instance.'
}
if (-not $webRunning -and @(Listener $WebPort).Count -eq 0 -and
    (Healthy ('http://127.0.0.1:' + $WebPort + '/'))) {
    Show-PortDiagnostics $WebPort 'frontend'
    throw 'Frontend already responds but TCP owner could not be established; refusing second instance.'
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
