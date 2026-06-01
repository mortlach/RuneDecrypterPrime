$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..\..")).Path

Set-Location $repoRoot

$pythonExe = "C:\Python\Python311\python.exe"
$runner = "tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_v1.py"
$logPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_live_canary_kept7003_2026-04-25.log"
$maxWallclockSeconds = 28800

$runnerAbs = Join-Path $repoRoot $runner
$logAbs = Join-Path $repoRoot $logPath
$logParent = Split-Path -Parent $logAbs
$outputBase = Join-Path $repoRoot "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1"

if (-not (Test-Path $pythonExe)) {
    throw "Missing python executable: $pythonExe"
}
if (-not (Test-Path $runnerAbs)) {
    throw "Missing runner: $runner"
}
if (-not (Test-Path $logParent)) {
    throw "Missing log parent: planning/projects/no_wli/50_console_and_watch_logs"
}
if (-not (Test-Path $outputBase)) {
    throw "Missing output base: output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1"
}

$runnerText = Get-Content -Path $runnerAbs -Raw
if ($runnerText -notmatch "LIVE_CANARY_LAUNCH_APPROVED = True") {
    Write-Host "launch_blocked guard=LIVE_CANARY_LAUNCH_APPROVED_FALSE runner=$runner"
    Write-Host "Set the hardcoded guard to True only after the Day 2 preflight and launch note are accepted."
    exit 2
}

$startedLocal = Get-Date
$budgetLocal = $startedLocal.AddSeconds($maxWallclockSeconds)

"launch_started runner=$runner log=$logPath" | Tee-Object -FilePath $logAbs
"budget_window started_local=$($startedLocal.ToString('yyyy-MM-dd HH:mm:ss zzz')) budget_target_local=$($budgetLocal.ToString('yyyy-MM-dd HH:mm:ss zzz')) max_wallclock_seconds=$maxWallclockSeconds" | Tee-Object -FilePath $logAbs -Append
"stop_rule watchdog kills the live canary process if elapsed reaches 08:00:00 before process completion" | Tee-Object -FilePath $logAbs -Append

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $pythonExe
$psi.Arguments = $runner
$psi.WorkingDirectory = $repoRoot
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi

$stdoutAction = {
    if ($EventArgs.Data) {
        Write-Host $EventArgs.Data
        Add-Content -Path $Event.MessageData -Value $EventArgs.Data
    }
}
$stderrAction = {
    if ($EventArgs.Data) {
        $line = "STDERR: $($EventArgs.Data)"
        Write-Host $line
        Add-Content -Path $Event.MessageData -Value $line
    }
}

$stdoutEvent = Register-ObjectEvent -InputObject $process -EventName OutputDataReceived -Action $stdoutAction -MessageData $logAbs
$stderrEvent = Register-ObjectEvent -InputObject $process -EventName ErrorDataReceived -Action $stderrAction -MessageData $logAbs

$started = $process.Start()
$process.BeginOutputReadLine()
$process.BeginErrorReadLine()
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$watchdogExit = 0

try {
    while (-not $process.HasExited) {
        Start-Sleep -Seconds 60
        $elapsed = [int]$stopwatch.Elapsed.TotalSeconds
        $remaining = [Math]::Max(0, $maxWallclockSeconds - $elapsed)
        $line = "watchdog_progress completed=0/1 elapsed_seconds=$elapsed remaining_seconds=$remaining cap_seconds=$maxWallclockSeconds"
        Write-Host $line
        Add-Content -Path $logAbs -Value $line
        if ($elapsed -ge $maxWallclockSeconds) {
            $watchdogExit = 124
            $line = "watchdog_stop reason=wallclock_cap elapsed_seconds=$elapsed cap_seconds=$maxWallclockSeconds"
            Write-Host $line
            Add-Content -Path $logAbs -Value $line
            Stop-Process -Id $process.Id -Force
            break
        }
    }
    $process.WaitForExit()
}
finally {
    Unregister-Event -SourceIdentifier $stdoutEvent.Name -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier $stderrEvent.Name -ErrorAction SilentlyContinue
    Remove-Job -Id $stdoutEvent.Id -Force -ErrorAction SilentlyContinue
    Remove-Job -Id $stderrEvent.Id -Force -ErrorAction SilentlyContinue
}

$exitCode = if ($watchdogExit -ne 0) { $watchdogExit } else { $process.ExitCode }
$elapsedFinal = [int]$stopwatch.Elapsed.TotalSeconds
"launch_finished exit_code=$exitCode elapsed_seconds=$elapsedFinal" | Tee-Object -FilePath $logAbs -Append
exit $exitCode
