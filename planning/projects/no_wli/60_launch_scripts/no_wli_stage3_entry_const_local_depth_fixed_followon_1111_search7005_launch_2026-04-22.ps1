$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..\..")).Path

Set-Location $repoRoot

$pythonExe = "C:\Python\Python311\python.exe"
$runner = "tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_fixed_followon_1111_search7005_v1.py"
$logPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_2026-04-22.log"

Write-Host "launch_started runner=$runner log=$logPath"
& $pythonExe $runner *>&1 | Tee-Object -FilePath $logPath
$exitCode = $LASTEXITCODE
Write-Host "launch_finished exit_code=$exitCode"
exit $exitCode
