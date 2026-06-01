$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
$RunnerRel = "tools\benchmarks\periodic_sub_trans\no_wli\analysis\fixed_instance_solver_development_v1\run_stage3_entry_const_local_depth_handoff_7004_v1.py"
$Runner = Join-Path $RepoRoot $RunnerRel
$LogRel = "planning\projects\no_wli\50_console_and_watch_logs\no_wli_stage3_entry_const_local_depth_handoff_7004_2026-05-01.log"
$LogPath = Join-Path $RepoRoot $LogRel
$BudgetSeconds = 21600
$HeartbeatSeconds = 60

Set-Location $RepoRoot
New-Item -ItemType Directory -Force -Path (Split-Path $LogPath -Parent) | Out-Null

function Write-WatchLine {
    param([string]$Message)
    $Message | Tee-Object -FilePath $LogPath -Append
}

Write-WatchLine ("[launch] run_label=stage3_entry_const_local_depth_handoff_7004_v1")
Write-WatchLine ("[launch] runner=$RunnerRel")
Write-WatchLine ("[launch] log=$LogRel")
Write-WatchLine ("[launch] budget_seconds=$BudgetSeconds")
Write-WatchLine ("[launch] started_utc=$((Get-Date).ToUniversalTime().ToString('s'))Z")

$Started = Get-Date
$Job = Start-Job -ScriptBlock {
    param($RepoRootArg, $RunnerArg)
    Set-Location $RepoRootArg
    py -3 $RunnerArg 2>&1
} -ArgumentList $RepoRoot, $Runner

$Completed = 0
while ($true) {
    Receive-Job $Job | Tee-Object -FilePath $LogPath -Append
    $Elapsed = [int]((Get-Date) - $Started).TotalSeconds
    $Remaining = [Math]::Max(0, $BudgetSeconds - $Elapsed)
    if ($Job.State -ne "Running") {
        $Completed = 1
        break
    }
    Write-WatchLine ("[watch] completed=0/1 elapsed_seconds=$Elapsed budget_seconds=$BudgetSeconds remaining_seconds=$Remaining")
    if ($Elapsed -ge $BudgetSeconds) {
        Write-WatchLine ("[watch] completed=0/1 elapsed_seconds=$Elapsed budget_reached=1 action=stop_job")
        Stop-Job $Job
        break
    }
    Start-Sleep -Seconds $HeartbeatSeconds
}

Receive-Job $Job | Tee-Object -FilePath $LogPath -Append
$FinalElapsed = [int]((Get-Date) - $Started).TotalSeconds
$FinalState = $Job.State
Remove-Job $Job -Force
Write-WatchLine ("[finish] completed=$Completed/1 elapsed_seconds=$FinalElapsed final_state=$FinalState finished_utc=$((Get-Date).ToUniversalTime().ToString('s'))Z")
