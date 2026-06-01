$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
Set-Location $RepoRoot

$LogRelPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_frontier_space_robustness_harvest_2026-05-01.log"
$LogParent = Split-Path $LogRelPath -Parent
New-Item -ItemType Directory -Force -Path $LogParent | Out-Null

$env:PYTHONUNBUFFERED = "1"
$ScriptRelPath = "tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_frontier_space_robustness_harvest_v1.py"

"[stage35_frontier_space_robustness_harvest] repo=$((Get-Location).Path)" | Tee-Object -FilePath $LogRelPath
"[stage35_frontier_space_robustness_harvest] script=$ScriptRelPath" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_frontier_space_robustness_harvest] log=$LogRelPath" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_frontier_space_robustness_harvest] source_rows=output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/stage35_guard_selector_frontier_runtime_rows.csv" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_frontier_space_robustness_harvest] max_wallclock_seconds=28800" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_frontier_space_robustness_harvest] per_cell_max_runtime_seconds=1800" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_frontier_space_robustness_harvest] max_cells=48" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_frontier_space_robustness_harvest] stop_condition=queue_exhausted_or_wallclock_budget_reached_or_first_cell_projection_over_budget" | Tee-Object -FilePath $LogRelPath -Append

py -3 $ScriptRelPath 2>&1 | Tee-Object -FilePath $LogRelPath -Append
$ExitCode = $LASTEXITCODE

"[stage35_frontier_space_robustness_harvest] exit_code=$ExitCode" | Tee-Object -FilePath $LogRelPath -Append
exit $ExitCode
