$ErrorActionPreference = "Stop"

$RunStatePath = "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_tune_v58_p5c1_seed511_stage35_baseline_selector_candidate_live_bounded_space_map_v1_smoke_single_1job.json"
$ArtifactGlob = "output/tools/benchmarks/periodic_sub_trans/no_wli/*/final_instances/fixture_fixture_001_p5_c1_l1000__text0__seed511.json"
$FixtureMatrixConfigPath = "tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py"
$AtlasScriptPath = "tools/benchmarks/periodic_sub_trans/no_wli/extract_space_map_v1_atlas.py"
$AtlasRootPath = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas"
$ScienceLogPath = "planning/projects/no_wli/10_full_logs/no_wli_science_run_log_2026-03-26.md"
$DataContractPath = "planning/projects/no_wli/30_analysis_specs/no_wli_partial_state_space_map_data_contract_2026-04-02.md"
$WatchLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_v58_watch_and_launch_v59_2026-04-03.log"
$LaunchScriptPath = "planning/projects/no_wli/60_launch_scripts/no_wli_v59_launch_ladder_small_2026-04-03.ps1"
$PollSeconds = 30
$MaxWaitSeconds = 14400

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

function Get-LatestArtifact {
    param([object]$State)

    $artifacts = @(Get-ChildItem $ArtifactGlob -ErrorAction SilentlyContinue)
    if ($artifacts.Count -eq 0) {
        return $null
    }

    $startedUtc = $null
    if ($null -ne $State -and $null -ne $State.started_utc) {
        $startedUtc = [datetime]$State.started_utc
    }
    if ($null -ne $startedUtc) {
        $freshArtifacts = @(
            $artifacts | Where-Object { $_.LastWriteTimeUtc -ge $startedUtc }
        )
        if ($freshArtifacts.Count -gt 0) {
            $artifacts = $freshArtifacts
        }
    }

    return $artifacts | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
}

function Get-PoolSummary {
    param(
        [object[]]$Pools,
        [string]$Boundary
    )
    return $Pools |
        Where-Object { [string]$_.stage_boundary -eq $Boundary } |
        Select-Object -First 1
}

$deadline = (Get-Date).AddSeconds($MaxWaitSeconds)
Write-WatchLog "[v58-watch] started run_state=$RunStatePath"

while ($true) {
    $state = Read-RunState
    if ($null -eq $state) {
        Write-WatchLog "[v58-watch] waiting state_file_missing=1"
    }
    else {
        $completedJobs = [int]$state.completed_jobs
        $remainingJobs = [int]$state.remaining_jobs
        $stoppedEarly = [int]$state.stopped_early
        $lastError = $state.last_error
        Write-WatchLog "[v58-watch] poll completed_jobs=$completedJobs remaining_jobs=$remainingJobs stopped_early=$stoppedEarly has_error=$($null -ne $lastError)"
        if ($null -ne $lastError) {
            $msg = @"
### 2026-04-03 v58 watcher result: failed smoke run

- watcher log:
  - $WatchLogPath
- run state:
  - $RunStatePath
- error type:
  - $($lastError.error_type)
- message:
  - $($lastError.message)

Next action:

- inspect v58 and do not launch v59 automatically
"@
            Append-DocSection -Path $ScienceLogPath -Text $msg
            Append-DocSection -Path $DataContractPath -Text $msg
            Write-WatchLog "[v58-watch] failed error_type=$($lastError.error_type)"
            exit 1
        }
        if ($completedJobs -ge 1 -or $remainingJobs -eq 0 -or $stoppedEarly -ne 0) {
            break
        }
    }
    if ((Get-Date) -ge $deadline) {
        Write-WatchLog "[v58-watch] timeout max_wait_seconds=$MaxWaitSeconds"
        exit 2
    }
    Start-Sleep -Seconds $PollSeconds
}

$finalState = Read-RunState
$artifact = Get-LatestArtifact -State $finalState
if ($null -eq $artifact) {
    Write-WatchLog "[v58-watch] completed_but_no_artifact"
    exit 3
}

$obj = Get-Content $artifact.FullName -Raw | ConvertFrom-Json
$space = $obj.stage3_diagnostics.space_map_v1
$bestMatch = [double]$obj.best_match_ratio
$bestStage = [string]$obj.best_stage
$acceptReason = [string]$obj.stage3_diagnostics.stage35_accept_reason
$topRunId = [string]$space.run_id
$poolRows = @($space.pool_summaries)
$partialRows = @($space.partial_state_rows)
$stage2Promoted = Get-PoolSummary -Pools $poolRows -Boundary "stage2_promoted"
$stage3Prep = Get-PoolSummary -Pools $poolRows -Boundary "stage3_prep"
$phasecPool = Get-PoolSummary -Pools $poolRows -Boundary "phaseC_pool"
$phasecStart = Get-PoolSummary -Pools $poolRows -Boundary "phaseC_start"
$stage35Seed = Get-PoolSummary -Pools $poolRows -Boundary "stage35_seed"
$stage35Archive = Get-PoolSummary -Pools $poolRows -Boundary "stage35_archive"
$artifactRel = $artifact.FullName.Replace((Get-Location).Path + "\", "").Replace("\", "/")

$bestMatchOk = [Math]::Abs($bestMatch - 1.0) -le 0.0000001
$runIdOk = -not [string]::IsNullOrWhiteSpace($topRunId)
$poolStatusOk = ($null -ne $stage2Promoted) -and
    ($null -ne $stage3Prep) -and
    ($null -ne $phasecPool) -and
    ($null -ne $phasecStart) -and
    ($null -ne $stage35Seed) -and
    ($null -ne $stage35Archive) -and
    (-not [string]::IsNullOrWhiteSpace([string]$stage2Promoted.pool_status)) -and
    (-not [string]::IsNullOrWhiteSpace([string]$stage3Prep.pool_status)) -and
    (-not [string]::IsNullOrWhiteSpace([string]$phasecPool.pool_status)) -and
    (-not [string]::IsNullOrWhiteSpace([string]$phasecStart.pool_status)) -and
    (-not [string]::IsNullOrWhiteSpace([string]$stage35Seed.pool_status)) -and
    (-not [string]::IsNullOrWhiteSpace([string]$stage35Archive.pool_status))
$rowCoverageOk = $partialRows.Count -gt 0

Write-WatchLog "[v58-watch] artifact=$artifactRel best_stage=$bestStage best_match=$bestMatch accept_reason=$acceptReason run_id=$topRunId"
Write-WatchLog "[v58-watch] pools stage2=$([string]$stage2Promoted.pool_status) stage3=$([string]$stage3Prep.pool_status) phasec_pool=$([string]$phasecPool.pool_status) phasec_start=$([string]$phasecStart.pool_status) stage35_seed=$([string]$stage35Seed.pool_status) stage35_archive=$([string]$stage35Archive.pool_status) partial_rows=$($partialRows.Count)"

if ($bestMatchOk -and $runIdOk -and $poolStatusOk -and $rowCoverageOk) {
    Write-WatchLog "[v58-watch] smoke_contract_pass=1 running_atlas=1"
    C:\Python\Python311\python.exe $AtlasScriptPath 2>&1 |
        Tee-Object -FilePath $WatchLogPath -Append
    $atlasRun = Get-ChildItem $AtlasRootPath -Directory -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
    $atlasRel = if ($null -eq $atlasRun) {
        ""
    }
    else {
        $atlasRun.FullName.Replace((Get-Location).Path + "\", "").Replace("\", "/")
    }

    $configText = Get-Content $FixtureMatrixConfigPath -Raw
    $newConfigText = $configText.Replace(
        'STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_single_p5"',
        'STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_ladder_small"'
    )
    if ($newConfigText -ne $configText) {
        Set-Content -Path $FixtureMatrixConfigPath -Value $newConfigText -Encoding UTF8
        Write-WatchLog "[v58-watch] switched_config_to_candidate_ladder_small=1"
    }
    else {
        Write-WatchLog "[v58-watch] switched_config_to_candidate_ladder_small=0 already_or_missing"
    }

    $msg = @"
### 2026-04-03 v58 watcher result: p5 smoke pass, v59 ladder launched

- artifact:
  - $artifactRel
- best_stage = $bestStage
- best_match_ratio = $bestMatch
- stage35_accept_reason = "$acceptReason"
- space_map_v1.run_id = $topRunId
- pool statuses:
  - stage2_promoted = "$([string]$stage2Promoted.pool_status)"
  - stage3_prep = "$([string]$stage3Prep.pool_status)"
  - phaseC_pool = "$([string]$phasecPool.pool_status)"
  - phaseC_start = "$([string]$phasecStart.pool_status)"
  - stage35_seed = "$([string]$stage35Seed.pool_status)"
  - stage35_archive = "$([string]$stage35Archive.pool_status)"
- partial_state_rows = $($partialRows.Count)
- atlas output:
  - $atlasRel
- next config:
  - STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "candidate_ladder_small"
  - RUN_SEEDS = (611, 711)
  - MAX_WALLCLOCK_SECONDS = 28800
- launched one-shot ladder run:
  - tune_v59_ladder_small_seed611_711_stage35_baseline_selector_candidate_live_bounded_space_map_v1_6job

Scope note:

- this is one unattended v58 -> v59 handoff only
- do not chain beyond v59 automatically
"@
    Append-DocSection -Path $ScienceLogPath -Text $msg
    Append-DocSection -Path $DataContractPath -Text $msg
    Write-WatchLog "[v58-watch] launching_v59=1 atlas=$atlasRel"
    Start-Process powershell -WorkingDirectory (Get-Location).Path -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-File',$LaunchScriptPath
    exit 0
}

$msgFail = @"
### 2026-04-03 v58 watcher result: smoke contract failed, v59 not launched

- artifact:
  - $artifactRel
- best_stage = $bestStage
- best_match_ratio = $bestMatch
- stage35_accept_reason = "$acceptReason"
- space_map_v1.run_id = $topRunId
- checks:
  - best_match_ok = $bestMatchOk
  - run_id_ok = $runIdOk
  - pool_status_ok = $poolStatusOk
  - row_coverage_ok = $rowCoverageOk

Next action:

- inspect v58, patch if needed, and rerun the smoke lane manually
"@
Append-DocSection -Path $ScienceLogPath -Text $msgFail
Append-DocSection -Path $DataContractPath -Text $msgFail
Write-WatchLog "[v58-watch] smoke_contract_pass=0 best_match_ok=$bestMatchOk run_id_ok=$runIdOk pool_status_ok=$poolStatusOk row_coverage_ok=$rowCoverageOk"
exit 4

