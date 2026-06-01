$ErrorActionPreference = "Stop"

$RunStatePath = "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v56_p5c1_seed511_stage35_baseline_selector_candidate_live_bounded_single_1job.json"
$ArtifactGlob = "output/tools/benchmarks/periodic_sub_trans/no_wli/*/final_instances/fixture_fixture_001_p5_c1_l1000__text0__seed511.json"
$FixtureMatrixConfigPath = "tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py"
$ScienceLogPath = "planning/projects/no_wli/10_full_logs/no_wli_science_run_log_2026-03-26.md"
$SpeedPlanPath = "planning/projects/no_wli/20_active_plans/no_wli_stage35_speed_focus_plan_2026-04-02.md"
$WatchLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_v56_watch_and_prepare_v55_2026-04-02.log"
$PollSeconds = 30
$MaxWaitSeconds = 10800

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

$deadline = (Get-Date).AddSeconds($MaxWaitSeconds)
Write-WatchLog "[v56-watch] started run_state=$RunStatePath"

while ($true) {
    $state = Read-RunState
    if ($null -eq $state) {
        Write-WatchLog "[v56-watch] waiting state_file_missing=1"
    }
    else {
        $completedJobs = [int]$state.completed_jobs
        $remainingJobs = [int]$state.remaining_jobs
        $stoppedEarly = [int]$state.stopped_early
        $lastError = $state.last_error
        Write-WatchLog "[v56-watch] poll completed_jobs=$completedJobs remaining_jobs=$remainingJobs stopped_early=$stoppedEarly has_error=$($null -ne $lastError)"
        if ($null -ne $lastError) {
            $msg = @"
### 2026-04-03 v56 watcher result: failed run

- watcher log:
  - $WatchLogPath
- run state:
  - $RunStatePath
- error type:
  - $($lastError.error_type)
- message:
  - $($lastError.message)

Next action:

- inspect the failure and patch/rerun v56 before switching to v55
"@
            Append-DocSection -Path $ScienceLogPath -Text $msg
            Append-DocSection -Path $SpeedPlanPath -Text $msg
            Write-WatchLog "[v56-watch] failed error_type=$($lastError.error_type)"
            exit 1
        }
        if ($completedJobs -ge 1 -or $remainingJobs -eq 0 -or $stoppedEarly -ne 0) {
            break
        }
    }
    if ((Get-Date) -ge $deadline) {
        Write-WatchLog "[v56-watch] timeout max_wait_seconds=$MaxWaitSeconds"
        exit 2
    }
    Start-Sleep -Seconds $PollSeconds
}

$artifact = Get-ChildItem $ArtifactGlob -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $artifact) {
    Write-WatchLog "[v56-watch] completed_but_no_artifact"
    exit 3
}

$obj = Get-Content $artifact.FullName -Raw | ConvertFrom-Json
$space = $obj.stage3_diagnostics.space_map_v1
$bestMatch = [double]$obj.best_match_ratio
$acceptReason = [string]$obj.stage3_diagnostics.stage35_accept_reason
$poolRows = @($space.pool_summaries)
$phasecPool = $poolRows | Where-Object { [string]$_.stage_boundary -eq "phaseC_start" } | Select-Object -First 1
$poolRunIds = @(
    $poolRows |
        Select-Object -ExpandProperty run_id -Unique |
        ForEach-Object { [string]$_ }
)
$partialRunIds = @(
    @($space.partial_state_rows) |
        Select-Object -ExpandProperty run_id -Unique |
        ForEach-Object { [string]$_ }
)
$phasecStatus = if ($null -eq $phasecPool) { "" } else { [string]$phasecPool.pool_status }
$runIdOk = ($poolRunIds.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($poolRunIds[0])) -and
    ($partialRunIds.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($partialRunIds[0]))
$phasecStatusOk = $phasecStatus -eq "not_run"
$bestMatchOk = [Math]::Abs($bestMatch - 1.0) -le 0.0000001
$artifactRel = $artifact.FullName.Replace((Get-Location).Path + "\", "").Replace("\", "/")

if ($runIdOk -and $phasecStatusOk -and $bestMatchOk) {
    $configText = Get-Content $FixtureMatrixConfigPath -Raw
    $newConfigText = $configText.Replace(
        'STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single_p5"',
        'STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single_p7"'
    )
    if ($newConfigText -ne $configText) {
        Set-Content -Path $FixtureMatrixConfigPath -Value $newConfigText -Encoding UTF8
        Write-WatchLog "[v56-watch] switched_config_to_candidate_single_p7=1"
    }
    else {
        Write-WatchLog "[v56-watch] switched_config_to_candidate_single_p7=0 already_or_missing"
    }
    $msg = @"
### 2026-04-03 v56 watcher result: pass, v55 prepared

- artifact:
  - $artifactRel
- best_match_ratio = $bestMatch
- stage35_accept_reason = "$acceptReason"
- space_map_v1.phaseC_start.pool_status = "$phasecStatus"
- pool run ids:
  - $([string]::Join(", ", $poolRunIds))
- partial-row run ids:
  - $([string]::Join(", ", $partialRunIds))
- config switched to:
  - STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single_p7"
- next prepared run:
  - tune_v55_p7c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job

Next action:

- run tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py
"@
    Append-DocSection -Path $ScienceLogPath -Text $msg
    Append-DocSection -Path $SpeedPlanPath -Text $msg
    Write-WatchLog "[v56-watch] pass artifact=$artifactRel best_match=$bestMatch phasec_pool_status=$phasecStatus run_id=$($poolRunIds[0])"
    exit 0
}

$msgFail = @"
### 2026-04-03 v56 watcher result: data-contract check failed

- artifact:
  - $artifactRel
- best_match_ratio = $bestMatch
- stage35_accept_reason = "$acceptReason"
- space_map_v1.phaseC_start.pool_status = "$phasecStatus"
- pool run ids:
  - $([string]::Join(", ", $poolRunIds))
- partial-row run ids:
  - $([string]::Join(", ", $partialRunIds))

Next action:

- inspect the artifact and patch/rerun v56
- do not switch to candidate_single_p7 yet
"@
Append-DocSection -Path $ScienceLogPath -Text $msgFail
Append-DocSection -Path $SpeedPlanPath -Text $msgFail
Write-WatchLog "[v56-watch] contract_fail best_match_ok=$bestMatchOk phasec_status_ok=$phasecStatusOk run_id_ok=$runIdOk"
exit 4

