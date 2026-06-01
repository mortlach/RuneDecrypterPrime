$ErrorActionPreference = "Stop"

$RunStatePath = "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v55_p7c1_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job.json"
$ArtifactGlob = "output/tools/benchmarks/periodic_sub_trans/no_wli/*/final_instances/fixture_fixture_001_p7_c1_l1000__text0__seed411.json"
$FixtureMatrixConfigPath = "tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py"
$ScienceLogPath = "planning/projects/no_wli/10_full_logs/no_wli_science_run_log_2026-03-26.md"
$SpeedPlanPath = "planning/projects/no_wli/20_active_plans/no_wli_stage35_speed_focus_plan_2026-04-02.md"
$WatchLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_v55_watch_and_launch_v57_2026-04-02.log"
$LaunchScriptPath = "planning/projects/no_wli/60_launch_scripts/no_wli_v57_launch_p9_2026-04-02.ps1"
$PollSeconds = 30
$MaxWaitSeconds = 21600

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
Write-WatchLog "[v55-watch] started run_state=$RunStatePath"

while ($true) {
    $state = Read-RunState
    if ($null -eq $state) {
        Write-WatchLog "[v55-watch] waiting state_file_missing=1"
    }
    else {
        $completedJobs = [int]$state.completed_jobs
        $remainingJobs = [int]$state.remaining_jobs
        $stoppedEarly = [int]$state.stopped_early
        $lastError = $state.last_error
        Write-WatchLog "[v55-watch] poll completed_jobs=$completedJobs remaining_jobs=$remainingJobs stopped_early=$stoppedEarly has_error=$($null -ne $lastError)"
        if ($null -ne $lastError) {
            $msg = @"
### 2026-04-03 v55 watcher result: failed run

- watcher log:
  - $WatchLogPath
- run state:
  - $RunStatePath
- error type:
  - $($lastError.error_type)
- message:
  - $($lastError.message)

Next action:

- inspect v55 and do not launch v57 automatically
"@
            Append-DocSection -Path $ScienceLogPath -Text $msg
            Append-DocSection -Path $SpeedPlanPath -Text $msg
            Write-WatchLog "[v55-watch] failed error_type=$($lastError.error_type)"
            exit 1
        }
        if ($completedJobs -ge 1 -or $remainingJobs -eq 0 -or $stoppedEarly -ne 0) {
            break
        }
    }
    if ((Get-Date) -ge $deadline) {
        Write-WatchLog "[v55-watch] timeout max_wait_seconds=$MaxWaitSeconds"
        exit 2
    }
    Start-Sleep -Seconds $PollSeconds
}

$artifact = Get-ChildItem $ArtifactGlob -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $artifact) {
    Write-WatchLog "[v55-watch] completed_but_no_artifact"
    exit 3
}

$obj = Get-Content $artifact.FullName -Raw | ConvertFrom-Json
$space = $obj.stage3_diagnostics.space_map_v1
$bestMatch = [double]$obj.best_match_ratio
$bestStage = [string]$obj.best_stage
$acceptReason = [string]$obj.stage3_diagnostics.stage35_accept_reason
$topRunId = [string]$space.run_id
$poolRows = @($space.pool_summaries)
$phasecPool = $poolRows |
    Where-Object { [string]$_.stage_boundary -eq "phaseC_start" } |
    Select-Object -First 1
$phasecStatus = if ($null -eq $phasecPool) { "" } else { [string]$phasecPool.pool_status }
$artifactRel = $artifact.FullName.Replace((Get-Location).Path + "\", "").Replace("\", "/")
$contractOk = (-not [string]::IsNullOrWhiteSpace($topRunId)) -and
    (-not [string]::IsNullOrWhiteSpace($phasecStatus)) -and
    ([Math]::Abs($bestMatch - 1.0) -le 0.0000001)

if ($contractOk) {
    $configText = Get-Content $FixtureMatrixConfigPath -Raw
    $newConfigText = $configText.Replace(
        'STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single_p7"',
        'STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single"'
    )
    if ($newConfigText -ne $configText) {
        Set-Content -Path $FixtureMatrixConfigPath -Value $newConfigText -Encoding UTF8
        Write-WatchLog "[v55-watch] switched_config_to_candidate_single=1"
    }
    else {
        Write-WatchLog "[v55-watch] switched_config_to_candidate_single=0 already_or_missing"
    }

    $msg = @"
### 2026-04-03 v55 watcher result: p7 pass, v57 p9 one-shot launched

- artifact:
  - $artifactRel
- best_stage = $bestStage
- best_match_ratio = $bestMatch
- stage35_accept_reason = "$acceptReason"
- space_map_v1.run_id = $topRunId
- space_map_v1.phaseC_start.pool_status = "$phasecStatus"
- config switched to:
  - STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single"
- launched one-shot p9 run:
  - tune_v57_p9c3_seed411_stage35_baseline_selector_candidate_live_bounded_single_1job

Scope note:

- this uses the one-time permission for a single p9 run after v55
"@
    Append-DocSection -Path $ScienceLogPath -Text $msg
    Append-DocSection -Path $SpeedPlanPath -Text $msg
    Write-WatchLog "[v55-watch] pass artifact=$artifactRel best_match=$bestMatch run_id=$topRunId launching_v57=1"
    Start-Process powershell -WorkingDirectory (Get-Location).Path -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-File',$LaunchScriptPath
    exit 0
}

$msgFail = @"
### 2026-04-03 v55 watcher result: p7 contract check failed, v57 not launched

- artifact:
  - $artifactRel
- best_stage = $bestStage
- best_match_ratio = $bestMatch
- stage35_accept_reason = "$acceptReason"
- space_map_v1.run_id = $topRunId
- space_map_v1.phaseC_start.pool_status = "$phasecStatus"

Next action:

- inspect v55 and patch/rerun manually
- do not start v57 yet
"@
Append-DocSection -Path $ScienceLogPath -Text $msgFail
Append-DocSection -Path $SpeedPlanPath -Text $msgFail
Write-WatchLog "[v55-watch] contract_fail best_match=$bestMatch run_id=$topRunId phasec_status=$phasecStatus"
exit 4

