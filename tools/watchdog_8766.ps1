# watchdog_8766.ps1
# Health probe + auto-recovery for the VideoAnalyzer-Transcribe service (port 8766).
#
# Why this exists:
#   nssm restarts the app when the PROCESS EXITS. It cannot detect a HUNG process
#   (port still open, HTTP not answering). This probe covers that case.
#   It also recovers the case where the SERVICE itself has been stopped.
#
# Behaviour:
#   - Probe http://127.0.0.1:8766/ with a 10s timeout.
#   - Healthy  -> write a timestamp to watchdog.heartbeat, log nothing, exit 0.
#   - Unhealthy-> if service Running: nssm restart (hang) ; else: nssm start.
#                Then re-probe once and log the result.
#
# Registered as scheduled task: VideoAnalyzer-8766-Watchdog (every 1 minute, S4U).

$ErrorActionPreference = 'Continue'

$svc    = 'VideoAnalyzer-Transcribe'
$nssm   = 'D:\fun-asr\tools\nssm-2.24\win64\nssm.exe'
$url    = 'http://127.0.0.1:8766/'
$logDir = 'C:\Users\EDY\Projects\video-analyzer\backend\logs'
$log    = Join-Path $logDir 'watchdog.log'
$hb     = Join-Path $logDir 'watchdog.heartbeat'

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

function Write-Log([string]$msg) {
    $line = "{0} {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
    $line | Out-File -FilePath $log -Encoding utf8 -Append
}

function Invoke-Probe {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
        if ($r.StatusCode -eq 200 -and $r.Content.Length -gt 100) { return $true }
        return $false
    } catch {
        return $false
    }
}

# rotate watchdog.log at 5 MB
if ((Test-Path $log) -and ((Get-Item $log).Length -gt 5242880)) {
    [System.IO.File]::Delete($log)
}

if (Invoke-Probe) {
    [System.IO.File]::WriteAllText($hb, (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    exit 0
}

Write-Log 'UNHEALTHY: http probe failed'

$state = 'NotFound'
try {
    $s = Get-Service -Name $svc -ErrorAction Stop
    $state = $s.Status.ToString()
} catch {
    $state = 'NotFound'
}

if ($state -eq 'Running') {
    Write-Log 'service is Running but not answering -> restart (assumed hang)'
    $null = & $nssm restart $svc 2>&1
} elseif ($state -eq 'Paused') {
    # nssm 的 Paused 状态 = "应用退出过快，nssm 已停止自动重启"。
    # 此时 `nssm start` 会被直接忽略（实测 2026-11-20 17:24 连试三次全部 STILL DOWN），
    # 必须先 stop 解除 Paused，再 start 才能真正把服务拉起来。
    Write-Log 'service state = Paused -> stop then start'
    $null = & $nssm stop $svc 2>&1
    Start-Sleep -Seconds 5
    $null = & $nssm start $svc 2>&1
} else {
    Write-Log ("service state = " + $state + " -> start")
    $null = & $nssm start $svc 2>&1
}

Start-Sleep -Seconds 20
$finalState = 'Unknown'
try { $finalState = (Get-Service -Name $svc -ErrorAction Stop).Status.ToString() } catch { }
if (Invoke-Probe) {
    Write-Log ("RECOVERED (service=" + $finalState + ")")
    [System.IO.File]::WriteAllText($hb, (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    exit 0
}

Write-Log ("STILL DOWN after recovery attempt (service=" + $finalState + ")")
exit 1
