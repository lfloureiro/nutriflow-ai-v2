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
    [switch]$VerifyApiCandidateOnly,
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
function SelectLoopbackSocketOwner([object[]]$connections) {
    # NutriFlow binds explicitly to IPv4 127.0.0.1. IPv6 listeners on the
    # same numerical port do not own HTTP requests to 127.0.0.1.
    # A wildcard IPv4 listener also covers loopback, but if both appear
    # with different PIDs the binding is ambiguous and must be rejected.
    $ipv4Owners = @($connections | Where-Object {
        $_.LocalAddress -eq '127.0.0.1' -or $_.LocalAddress -eq '0.0.0.0'
    } | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($ipv4Owners.Count -eq 1) { return [int]$ipv4Owners[0] }
    return $null
}
function VerifiedServiceProcess([int]$port,[string]$role) {
    $connections = @(Listener $port)
    $owners = @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($owners.Count -eq 0) { return $null }
    if ($owners.Count -eq 1) {
        $ownerId = [int]$owners[0]
    } else {
        $ownerId = SelectLoopbackSocketOwner $connections
        if ($null -eq $ownerId) {
            Write-Warning ('Port ' + $port + ' has multiple TCP owners without a ' +
                'unique IPv4 loopback listener. No process selected.')
            Show-PortDiagnostics $port $role
            return $null
        }
        Write-Warning ('Port ' + $port + ' has multiple TCP owners; using unique ' +
            'IPv4 loopback owner PID ' + $ownerId + ', ignoring unrelated IPv6 listeners.')
    }
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
        $valid = ($executableName -match '^(python(?:w)?|uvicorn)[.]exe$') -and
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
function SelectSocketApiCandidate([object[]]$candidateProcesses,[int[]]$owners) {
    $socketMatches = @($candidateProcesses | Where-Object { $owners -contains $_.Id })
    if ($socketMatches.Count -eq 1) { return $socketMatches[0] }
    return $null
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
    $socketOwner = SelectSocketApiCandidate $candidateProcesses $owners
    if ($socketOwner) {
        Write-Host ('Verified Uvicorn socket owner on port ' + $port +
            ': PID ' + $socketOwner.Id)
        return $socketOwner
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
function TestLocalFrontendPid([int]$port,[int]$processId) {
    # Require NutriFlow's live Vite signature and Node's exact Vite
    # entrypoint from this checkout. Never adopt arbitrary Node processes.
    if (-not (Test-NutriFlowFrontend $port)) { return $false }
    $info = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $processId) -ErrorAction SilentlyContinue
    if (-not $info -or -not $info.CommandLine) { return $false }
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if (-not $process -or $process.ProcessName -ine 'node') { return $false }
    $line = ([string]$info.CommandLine).Replace('/', '\')
    $expectedVite = Join-Path $webDir 'node_modules\vite\bin\vite.js'
    return $line.IndexOf($expectedVite, [StringComparison]::OrdinalIgnoreCase) -ge 0
}
function FindLocalFrontendProcess([int]$port) {
    if (-not (Test-NutriFlowFrontend $port)) { return $null }
    $candidates = @()
    foreach ($info in @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction Stop)) {
        if (TestLocalFrontendPid $port ([int]$info.ProcessId)) {
            $process = Get-Process -Id ([int]$info.ProcessId) -ErrorAction SilentlyContinue
            if ($process) { $candidates += $process }
        }
    }
    if ($candidates.Count -eq 1) {
        Write-Host ('Found matching NutriFlow Vite process PID ' + $candidates[0].Id)
        return $candidates[0]
    }
    if ($candidates.Count -gt 1) {
        # Only the actual TCP owner may be chosen without ambiguity.
        $owners = @(Listener $port | Select-Object -ExpandProperty OwningProcess -Unique)
        $socketMatches = @($candidates | Where-Object { $owners -contains $_.Id })
        if ($socketMatches.Count -eq 1) { return $socketMatches[0] }
        foreach ($candidate in $candidates) {
            Write-Host ('Vite candidate PID ' + $candidate.Id +
                ' StartUTC=' + $candidate.StartTime.ToUniversalTime().ToString('o'))
        }
        throw ('Multiple NutriFlow Vite processes found on port ' + $port +
            ' with no unique socket owner. No process terminated.')
    }
    return $null
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
function SelectFreshApiLaunch($launched,$listeners,[string]$executable,[string[]]$arguments,[string]$expectedPython) {
    # Only for a process this invocation of deploy.ps1 created *after*
    # observing a free port. Never use to adopt an arbitrary running server.
    if ($null -eq $launched -or $launched.ProcessName -notmatch '^python') { return $null }
    if ($executable -ine $expectedPython -or
        $arguments.Count -lt 7 -or
        $arguments[0] -ne '-m' -or
        $arguments[1] -ne 'uvicorn' -or
        $arguments[2] -ne 'app.main:app') {
        return $null
    }
    # A different socket owner is a conflict, not proof this fresh launch owns it.
    $otherOwners = @($listeners | Where-Object { [int]$_ -ne [int]$launched.Id })
    if ($otherOwners.Count -gt 0) { return $null }
    return $launched
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
        if ($process.ProcessName -ieq 'node' -and
            (TestLocalFrontendPid $port $process.Id)) {
            return $process
        }
        # A fresh process managed by this deploy can lack Windows TCP owner
        # information. Trust its saved PID only with exact start time (checked
        # above), expected process family and the live NutriFlow signature.
        # This exemption never applies to adopted/legacy processes.
        if (-not (IsTrustedLaunch $entry)) { return $null }
        if ($process.ProcessName -ieq 'node') {
            if (-not (Test-NutriFlowFrontend $port)) { return $null }
        } elseif ($process.ProcessName -match '^python') {
            # Never keep managing a trusted Python PID if Windows now exposes
            # a different socket owner: that is an identity conflict.
            if ($listeners.Count -gt 0) { return $null }
            if (-not (Test-NutriFlowApi $port)) { return $null }
        } else {
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
    if (-not $process -and $role -eq 'frontend') {
        $process = FindLocalFrontendProcess $port
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
function WaitPortFree([int]$port,[string]$role,[int]$seconds=12) {
    # A Windows Node/Vite listener can linger or be recreated briefly after
    # its recorded PID exits. Do not select or terminate a second process.
    # Require several consecutive clear samples before launching.
    $clearSamples = 0
    $attempts = [Math]::Max(1, $seconds * 4)
    for ($attempt = 0; $attempt -lt $attempts; $attempt++) {
        $listeners = @(Listener $port)
        $responding = if ($role -eq 'api') {
            Healthy ('http://127.0.0.1:' + $port + '/openapi.json')
        } else {
            Healthy ('http://127.0.0.1:' + $port + '/')
        }
        if ($listeners.Count -eq 0 -and -not $responding) {
            $clearSamples++
            if ($clearSamples -ge 4) { return $true }
        } else {
            $clearSamples = 0
        }
        Start-Sleep -Milliseconds 250
    }
    Show-PortDiagnostics $port $role
    return $false
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
    $role = if ($port -eq $WebPort) { 'frontend' } else { 'api' }
    if (-not (WaitPortFree $port $role)) {
        throw ('Port ' + $port + ' remains occupied or was reopened after stopping PID ' +
            $process.Id + '. Inspect the owner above; no other process was terminated.')
    }
}
function Launch([string]$exe,[string[]]$arg,[string]$cwd,[string]$name,[int]$port,[string]$url) {
    # A just-stopped Vite process may release/reacquire the listener during
    # Windows teardown. Wait for a stable free port instead of racing it.
    $role = if ($name -like 'frontend*') { 'frontend' } else { 'api' }
    if (-not (WaitPortFree $port $role)) {
        throw ('Port ' + $port + ' already responds or has a listener. Refusing second ' +
            $name + '; no untracked process was terminated.')
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
                $connections = @(Listener $port)
                $socketOwner = SelectLoopbackSocketOwner $connections
                if ($null -ne $socketOwner) {
                    $socketProc = Get-Process -Id $socketOwner -ErrorAction SilentlyContinue
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
        if (-not $proc -and $role -eq 'api') {
            # Uvicorn has no --reload here: its exact Start-Process PID is
            # authoritative when TCP ownership is missing. Require the precise
            # checkout Python, exact app entrypoint/port, a healthy NutriFlow
            # OpenAPI response and no contradictory TCP owner.
            $direct = Get-Process -Id $started.Id -ErrorAction SilentlyContinue
            $expectedPython = Join-Path $root '.venv\Scripts\python.exe'
            $isExpectedPort = $false
            for ($i=0; $i -lt ($arg.Count - 1); $i++) {
                if ($arg[$i] -eq '--port' -and [string]$arg[$i + 1] -eq [string]$port) {
                    $isExpectedPort = $true
                }
            }
            if ($isExpectedPort -and (Test-NutriFlowApi $port)) {
                $owners = @(Listener $port | Select-Object -ExpandProperty OwningProcess -Unique)
                $proc = SelectFreshApiLaunch $direct $owners $exe $arg $expectedPython
                if ($proc) {
                    $trustedLaunch = $true
                    Write-Warning ('Accepted freshly launched NutriFlow API PID ' +
                        $proc.Id + ' with verified launch arguments and OpenAPI identity; ' +
                        'Windows reported no usable TCP owner.')
                }
            }
        }
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
            $liveConnections = @(Listener $port)
            $loopbackOwner = SelectLoopbackSocketOwner $liveConnections
            # A directly launched process is trusted only if Windows does
            # not show a different IPv4 listener. Other IPv6 owners are
            # irrelevant to this explicit IPv4 Vite launch.
            $noContradictoryOwner = $liveConnections.Count -eq 0 -or
                ($null -ne $direct -and $null -ne $loopbackOwner -and
                    $loopbackOwner -eq $direct.Id)
            if ($direct -and $direct.ProcessName -ieq 'node' -and
                $exe -ieq (Executable 'node') -and
                $arg.Count -gt 0 -and
                [string]$arg[0] -ieq $expectedScript -and
                $noContradictoryOwner -and
                (Test-NutriFlowFrontend $port)) {
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
if ($VerifyApiCandidateOnly) {
    # Pure tests for mixed IPv4/IPv6 ownership: no process access or sockets.
    $mixedListeners = @(
        [pscustomobject]@{ LocalAddress='127.0.0.1'; OwningProcess=101 },
        [pscustomobject]@{ LocalAddress='::1'; OwningProcess=202 }
    )
    if ((SelectLoopbackSocketOwner $mixedListeners) -ne 101) {
        throw 'IPv4 NutriFlow listener must win over unrelated IPv6 listener.'
    }
    $conflictingListeners = @(
        [pscustomobject]@{ LocalAddress='127.0.0.1'; OwningProcess=101 },
        [pscustomobject]@{ LocalAddress='0.0.0.0'; OwningProcess=202 }
    )
    if ($null -ne (SelectLoopbackSocketOwner $conflictingListeners)) {
        throw 'Two distinct IPv4 owners must remain ambiguous.'
    }
    $onlyIpv6 = @([pscustomobject]@{ LocalAddress='::1'; OwningProcess=202 })
    if ($null -ne (SelectLoopbackSocketOwner $onlyIpv6)) {
        throw 'IPv6 listener alone must not be trusted for IPv4 NutriFlow.'
    }
    # Verify executable identity using the same regex as the runtime path.
    $apiExePattern = '^(python(?:w)?|uvicorn)[.]exe$'
    if ('python.exe' -notmatch $apiExePattern -or
        'pythonw.exe' -notmatch $apiExePattern -or
        'uvicorn.exe' -notmatch $apiExePattern -or
        'node.exe' -match $apiExePattern) {
        throw 'PowerShell Python executable identity regression.'
    }
    # No processes are started or stopped. Simulate duplicate Uvicorn
    # candidates and verify that the TCP owner wins, never the older PID.
    $candidates = @(
        [pscustomobject]@{ Id=101 },
        [pscustomobject]@{ Id=202 }
    )
    $winner = SelectSocketApiCandidate $candidates @([int]202)
    if (-not $winner -or $winner.Id -ne 202) {
        throw 'Failed to select the sole TCP-owning Uvicorn process.'
    }
    $ambiguous = SelectSocketApiCandidate $candidates @()
    if ($null -ne $ambiguous) {
        throw 'Ambiguous API candidates must not be selected automatically.'
    }
    $multiple = SelectSocketApiCandidate $candidates @([int]101,[int]202)
    if ($null -ne $multiple) {
        throw 'Multiple socket owners must not select a process automatically.'
    }
    # Freshly launched API can be verified without a TCP owner, but not
    # when an unrelated process owns the port or a different script was used.
    $fakeApi = [pscustomobject]@{ Id=303; ProcessName='python' }
    $pythonPath = Join-Path $root '.venv\Scripts\python.exe'
    $apiArgs = @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$ApiPort")
    $fresh = SelectFreshApiLaunch $fakeApi @() $pythonPath $apiArgs $pythonPath
    if (-not $fresh -or $fresh.Id -ne 303) {
        throw 'Fresh API process must be selectable without a TCP owner.'
    }
    if ($null -ne (SelectFreshApiLaunch $fakeApi @([int]404) $pythonPath $apiArgs $pythonPath)) {
        throw 'Foreign socket owner must reject fresh API process.'
    }
    if ($null -ne (SelectFreshApiLaunch $fakeApi @() 'C:\other\python.exe' $apiArgs $pythonPath)) {
        throw 'Unexpected Python executable must reject fresh API process.'
    }
    Write-Host 'Windows duplicate-Uvicorn and fresh API launch verification tests passed.'
    exit 0
}
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
