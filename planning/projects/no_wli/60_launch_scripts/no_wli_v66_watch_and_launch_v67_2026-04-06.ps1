$ErrorActionPreference = "Stop"

$RunStatePath = "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v66_p9c3_seed911_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job.json"
$RunEventsPath = "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_tune_v66_p9c3_seed911_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job.jsonl"
$WatchLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_v66_watch_and_launch_v67_2026-04-06.log"
$LaunchScriptPath = "planning/projects/no_wli/60_launch_scripts/no_wli_v67_launch_seed1011_2026-04-06.ps1"
$ScienceLogPath = "planning/projects/no_wli/10_full_logs/no_wli_science_run_log_2026-03-26.md"
$PollSeconds = 30
$MaxWaitSeconds = 43200

function Write-WatchLog {
    param([string]$Message)
    $line = "$((Get-Date).ToUniversalTime().ToString('o')) $Message"
    $line | Tee-Object -FilePath $WatchLogPath -Append
}

function Append-DocSection {
    param(
        [string]$Path,
        [string]$Text
    )
    Add-Content -Path $Path -Value ""
    Add-Content -Path $Path -Value $Text
}

function Read-RunState {
    if (!(Test-Path $RunStatePath)) {
        return $null
    }
    return Get-Content $RunStatePath -Raw | ConvertFrom-Json
}

function Get-LastJobError {
    if (!(Test-Path $RunEventsPath)) {
        return $null
    }
    $rows = Get-Content $RunEventsPath | Where-Object { $_.Trim().Length -gt 0 }
    $jobErrorRow = $rows |
        ForEach-Object { $_ | ConvertFrom-Json } |
        Where-Object { [string]$_.event -eq "job_error" } |
        Select-Object -Last 1
    return $jobErrorRow
}

$deadline = (Get-Date).AddSeconds($MaxWaitSeconds)
Write-WatchLog "[v66-watch] started run_state=$RunStatePath"

while ($true) {
    $state = Read-RunState
    $lastError = Get-LastJobError
    if ($null -eq $state) {
        Write-WatchLog "[v66-watch] waiting state_file_missing=1"
    }
    else {
        $completedJobs = [int]$state.completed_jobs
        $plannedJobs = [int]$state.planned_job_count
        $remainingJobs = [int]$state.remaining_jobs
        $stoppedEarly = [int]$state.stopped_early
        $stateError = $state.last_error
        Write-WatchLog "[v66-watch] poll completed_jobs=$completedJobs planned_jobs=$plannedJobs remaining_jobs=$remainingJobs stopped_early=$stoppedEarly has_state_error=$($null -ne $stateError) has_job_error=$($null -ne $lastError)"
        if ($null -ne $stateError -or $null -ne $lastError) {
            break
        }
        if ($completedJobs -ge $plannedJobs -and $plannedJobs -gt 0) {
            break
        }
        if ($remainingJobs -eq 0 -or $stoppedEarly -ne 0) {
            break
        }
    }
    if ((Get-Date) -ge $deadline) {
        Write-WatchLog "[v66-watch] timeout max_wait_seconds=$MaxWaitSeconds"
        exit 2
    }
    Start-Sleep -Seconds $PollSeconds
}

$finalState = Read-RunState
$lastError = Get-LastJobError
$completedJobs = if ($null -eq $finalState) { 0 } else { [int]$finalState.completed_jobs }
$plannedJobs = if ($null -eq $finalState) { 0 } else { [int]$finalState.planned_job_count }
$remainingJobs = if ($null -eq $finalState) { 0 } else { [int]$finalState.remaining_jobs }
$stoppedEarly = if ($null -eq $finalState) { 1 } else { [int]$finalState.stopped_early }
$stateError = if ($null -eq $finalState) { $null } else { $finalState.last_error }

if ($null -ne $stateError -or $null -ne $lastError -or $stoppedEarly -ne 0 -or $completedJobs -lt $plannedJobs) {
    $errorType = if ($null -ne $stateError) {
        [string]$stateError.error_type
    }
    elseif ($null -ne $lastError) {
        [string]$lastError.error_type
    }
    else {
        "incomplete_or_stopped_early"
    }
    $errorMessage = if ($null -ne $stateError) {
        [string]$stateError.error
    }
    elseif ($null -ne $lastError) {
        [string]$lastError.error
    }
    else {
        "completed_jobs=$completedJobs planned_jobs=$plannedJobs remaining_jobs=$remainingJobs stopped_early=$stoppedEarly"
    }
    $msg = @"
### 2026-04-06 v66 watcher result: no v67 auto-launch

- watcher log:
  - $WatchLogPath
- run state:
  - $RunStatePath
- completed_jobs = $completedJobs
- planned_job_count = $plannedJobs
- remaining_jobs = $remainingJobs
- stopped_early = $stoppedEarly
- error_type = $errorType
- message = $errorMessage

Next action:

- inspect v66 before starting the next hard-seed run manually
"@
    Append-DocSection -Path $ScienceLogPath -Text $msg
    Write-WatchLog "[v66-watch] launch_v67=0 error_type=$errorType"
    exit 1
}

$msg = @"
### 2026-04-06 v66 watcher result: clean completion, v67 launched

- watcher log:
  - $WatchLogPath
- completed_jobs = $completedJobs
- planned_job_count = $plannedJobs
- remaining_jobs = $remainingJobs
- stopped_early = $stoppedEarly
- next run:
  - tune_v67_p9c3_seed1011_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job
- launch script:
  - $LaunchScriptPath

Scope note:

- this is a one-shot v66 -> v67 handoff only
- no auto-chain beyond v67
"@
Append-DocSection -Path $ScienceLogPath -Text $msg
Write-WatchLog "[v66-watch] launch_v67=1"
Start-Process powershell -WorkingDirectory (Get-Location).Path -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-File',$LaunchScriptPath
exit 0

