$ErrorActionPreference = "Stop"

$CurrentRunLabel = "stage1_fwd_full_1k_pc_b"
$NextRunLabel = "stage1_fwd_full_1k_chunks_1000_1999"
$NextRunMode = "stage1_fwd_full_1k"
$NextChunkStartIndex = 1000
$NextNumCleanChunksThisRun = 1000
$ExpectedCurrentNextChunkStart = 1000
$PollSeconds = 60
$IntendedNextRunBudgetHours = 4.5

$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDir = Split-Path -Parent $ScriptPath
$RepoRoot = $ScriptDir
while ($RepoRoot -and -not (Test-Path (Join-Path $RepoRoot "AGENTS.md"))) {
    $Parent = Split-Path -Parent $RepoRoot
    if ($Parent -eq $RepoRoot) {
        throw "Could not resolve repo root from script path."
    }
    $RepoRoot = $Parent
}
Set-Location -LiteralPath $RepoRoot

$RunnerRel = "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_runeberg_nose_damage_ladder_v1.py"
$TestRel = "tests/tools/test_phaseB_runeberg_nose_damage_ladder_v1.py"
$CurrentOutputRel = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/$CurrentRunLabel"
$NextOutputRel = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/$NextRunLabel"
$LogDirRel = "output/logs"
$QueueLogRel = "$LogDirRel/${NextRunLabel}_queue.log"
$NextRunLogRel = "$LogDirRel/${NextRunLabel}_run.log"

function Resolve-RepoRelativePath([string]$RelPath) {
    $Full = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $RelPath))
    $RootFull = [System.IO.Path]::GetFullPath($RepoRoot)
    if (-not $Full.StartsWith($RootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes repo root: $RelPath"
    }
    return $Full
}

function Write-QueueLog([string]$Message) {
    $Stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $Line = "[$Stamp] $Message"
    Write-Host $Line
    Add-Content -Path (Resolve-RepoRelativePath $QueueLogRel) -Value $Line
}

New-Item -ItemType Directory -Path (Resolve-RepoRelativePath $LogDirRel) -Force | Out-Null
New-Item -ItemType Directory -Path (Resolve-RepoRelativePath (Split-Path -Parent $NextOutputRel)) -Force | Out-Null

$NextOutput = Resolve-RepoRelativePath $NextOutputRel
$NextRunLog = Resolve-RepoRelativePath $NextRunLogRel
if (Test-Path $NextOutput) {
    throw "Refusing to overwrite existing output directory: $NextOutputRel"
}
if (Test-Path $NextRunLog) {
    throw "Refusing to overwrite existing run log: $NextRunLogRel"
}

Write-QueueLog "Queued follow-up run $NextRunLabel."
Write-QueueLog "Range: chunk_start=$NextChunkStartIndex count=$NextNumCleanChunksThisRun; intended wallclock budget ${IntendedNextRunBudgetHours}h."
Write-QueueLog "Stop condition: wait until $CurrentRunLabel is complete with next_chunk_start_index=$ExpectedCurrentNextChunkStart, then run tests and launch one follow-up benchmark only."

$WaitStart = Get-Date
while ($true) {
    $StatePath = Resolve-RepoRelativePath "$CurrentOutputRel/run_state.json"
    $FinalPath = Resolve-RepoRelativePath "$CurrentOutputRel/final_summary.json"
    if (-not (Test-Path $StatePath)) {
        Write-QueueLog "Waiting: current run_state.json not present yet."
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    $State = Get-Content -Path $StatePath -Raw | ConvertFrom-Json
    $ElapsedWait = [int]((Get-Date) - $WaitStart).TotalSeconds
    Write-QueueLog "Current status=$($State.status) samples=$($State.samples_done)/$($State.estimated_total_samples) chunks_seen=$($State.actual_chunks_used) wait_elapsed=${ElapsedWait}s."

    if ($State.status -eq "failed") {
        throw "Current run failed; follow-up launch blocked."
    }
    if ($State.status -eq "complete") {
        if (-not (Test-Path $FinalPath)) {
            throw "Current run is complete but final_summary.json is missing."
        }
        $Final = Get-Content -Path $FinalPath -Raw | ConvertFrom-Json
        if ($Final.status -ne "complete") {
            throw "Current final_summary status is not complete: $($Final.status)"
        }
        if ([int]$Final.next_chunk_start_index -ne $ExpectedCurrentNextChunkStart) {
            throw "Current next_chunk_start_index=$($Final.next_chunk_start_index), expected $ExpectedCurrentNextChunkStart."
        }
        if ([int]$Final.actual_chunks_used -ne 500) {
            throw "Current actual_chunks_used=$($Final.actual_chunks_used), expected 500."
        }
        break
    }

    Start-Sleep -Seconds $PollSeconds
}

Write-QueueLog "Current run completed cleanly; preparing $NextRunLabel."

$RunnerPath = Resolve-RepoRelativePath $RunnerRel
$RunnerText = Get-Content -Path $RunnerPath -Raw
$RunnerText = $RunnerText -replace 'RUN_LABEL = "[^"]+"', "RUN_LABEL = `"$NextRunLabel`""
$RunnerText = $RunnerText -replace 'RUN_MODE = "[^"]+"  #', "RUN_MODE = `"$NextRunMode`"  #"
$RunnerText = $RunnerText -replace 'CHUNK_START_INDEX = \d+', "CHUNK_START_INDEX = $NextChunkStartIndex"
$RunnerText = $RunnerText -replace 'NUM_CLEAN_CHUNKS_THIS_RUN = \d+', "NUM_CLEAN_CHUNKS_THIS_RUN = $NextNumCleanChunksThisRun"
$RunnerText = $RunnerText -replace '"stage1_fwd_full_1k_pc_b"', "`"$NextRunLabel`""
Set-Content -Path $RunnerPath -Value $RunnerText -Encoding UTF8

$env:PYTHONPATH = "src"
Write-QueueLog "Running preflight tests: $TestRel"
python -m pytest $TestRel 2>&1 | Tee-Object -FilePath (Resolve-RepoRelativePath $QueueLogRel) -Append
if ($LASTEXITCODE -ne 0) {
    throw "Preflight tests failed; follow-up benchmark not launched."
}

Write-QueueLog "Launching benchmark: $NextRunLabel"
Write-QueueLog "Progress will stream to $NextRunLogRel."
python $RunnerRel 2>&1 | Tee-Object -FilePath $NextRunLogRel
$ExitCode = $LASTEXITCODE
Write-QueueLog "Benchmark exited with code $ExitCode."
exit $ExitCode
