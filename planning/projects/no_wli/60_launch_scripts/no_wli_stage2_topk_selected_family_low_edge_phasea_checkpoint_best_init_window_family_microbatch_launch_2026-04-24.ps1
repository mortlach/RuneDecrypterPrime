$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..\..")).Path

Set-Location $repoRoot

$pythonExe = "C:\Python\Python311\python.exe"
$runner = "tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_v1.py"
$logPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_2026-04-24.log"
$startedLocal = Get-Date
$budgetLocal = $startedLocal.AddMinutes(90)

Write-Host "launch_started runner=$runner log=$logPath"
Write-Host "budget_window started_local=$($startedLocal.ToString('yyyy-MM-dd HH:mm:ss zzz')) budget_target_local=$($budgetLocal.ToString('yyyy-MM-dd HH:mm:ss zzz'))"
Write-Host "stop_rule the Python runner will stop launching new lanes if the observed projection exceeds the 01:30:00 budget"

& $pythonExe $runner *>&1 | Tee-Object -FilePath $logPath
$exitCode = $LASTEXITCODE
Write-Host "launch_finished exit_code=$exitCode"
exit $exitCode
