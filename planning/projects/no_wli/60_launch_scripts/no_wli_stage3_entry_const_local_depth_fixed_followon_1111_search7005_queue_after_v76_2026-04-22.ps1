$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..\..")).Path

Set-Location $repoRoot

$currentRunStatePath = Join-Path $repoRoot "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v76_fixed_p9c3_1111_search7004_stage35_entry_const_local_depth_compare_2job.json"
$launchScript = (Resolve-Path (Join-Path $scriptDir "no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_launch_2026-04-22.ps1")).Path
$queueLogPath = Join-Path $repoRoot "planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_queue_2026-04-22.log"
$cutoffLocal = Get-Date "2026-04-22T01:15:00"
$pollSeconds = 300

function Write-QueueLog {
    param(
        [string]$Message
    )
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"), $Message
    Write-Host $line
    Add-Content -Path $queueLogPath -Value $line
}

Write-QueueLog "queue_started wait_for=$(Split-Path -Leaf $currentRunStatePath) cutoff_local=$($cutoffLocal.ToString('yyyy-MM-ddTHH:mm:ssK'))"

while ($true) {
    if (-not (Test-Path $currentRunStatePath)) {
        if ((Get-Date) -ge $cutoffLocal) {
            Write-QueueLog "queue_aborted reason=current_run_state_missing_at_cutoff"
            exit 0
        }
        Write-QueueLog "waiting reason=current_run_state_missing"
        Start-Sleep -Seconds 60
        continue
    }

    $state = Get-Content $currentRunStatePath | ConvertFrom-Json
    $completed = [int]$state.completed_jobs
    $total = [int]$state.total_jobs
    $updatedUtc = [string]$state.updated_utc

    Write-QueueLog "poll completed=$completed total=$total updated_utc=$updatedUtc"

    if ($total -gt 0 -and $completed -ge $total) {
        break
    }

    if ((Get-Date) -ge $cutoffLocal) {
        Write-QueueLog "queue_aborted reason=cutoff_reached_before_current_completed"
        exit 0
    }

    Start-Sleep -Seconds $pollSeconds
}

if ((Get-Date) -ge $cutoffLocal) {
    Write-QueueLog "queue_aborted reason=current_completed_after_cutoff"
    exit 0
}

Write-QueueLog "launching_followon script=$(Split-Path -Leaf $launchScript)"
& $launchScript
$exitCode = $LASTEXITCODE
Write-QueueLog "followon_finished exit_code=$exitCode"
exit $exitCode
