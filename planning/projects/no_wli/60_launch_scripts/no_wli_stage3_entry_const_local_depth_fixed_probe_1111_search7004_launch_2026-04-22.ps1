$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..\..")).Path

Set-Location $repoRoot

$pythonExe = "C:\Python\Python311\python.exe"
$runner = "tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_fixed_probe_1111_search7004_v1.py"
$logPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_fixed_probe_1111_search7004_2026-04-22.log"
$startedLocal = Get-Date
$stopLocal = $startedLocal.AddHours(8)

Write-Host "launch_started runner=$runner log=$logPath"
Write-Host "budget_window started_local=$($startedLocal.ToString('yyyy-MM-dd HH:mm:ss zzz')) stop_by_local=$($stopLocal.ToString('yyyy-MM-dd HH:mm:ss zzz'))"
Write-Host "manual_stop_rule if no normal completion artifacts exist by stop_by_local, kill the run and record it as operationally incomplete"

& $pythonExe $runner *>&1 | Tee-Object -FilePath $logPath
$exitCode = $LASTEXITCODE
Write-Host "launch_finished exit_code=$exitCode"
exit $exitCode
