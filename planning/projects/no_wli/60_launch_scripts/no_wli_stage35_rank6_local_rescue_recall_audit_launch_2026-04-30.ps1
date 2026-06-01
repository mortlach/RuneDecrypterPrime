$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
Set-Location $RepoRoot

$LogRelPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_rank6_local_rescue_recall_audit_2026-04-30.log"
$LogParent = Split-Path $LogRelPath -Parent
New-Item -ItemType Directory -Force -Path $LogParent | Out-Null

$env:PYTHONUNBUFFERED = "1"
$ScriptRelPath = "tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_rank6_local_rescue_recall_audit_v1.py"

"[stage35_rank6_local_rescue_recall_audit] repo=$((Get-Location).Path)" | Tee-Object -FilePath $LogRelPath
"[stage35_rank6_local_rescue_recall_audit] script=$ScriptRelPath" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_rank6_local_rescue_recall_audit] log=$LogRelPath" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_rank6_local_rescue_recall_audit] source_join_rows=output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/stage35_guard_selector_frontier_deepening_join_rows.csv" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_rank6_local_rescue_recall_audit] max_wallclock_seconds=2700" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_rank6_local_rescue_recall_audit] per_cell_max_runtime_seconds=600" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_rank6_local_rescue_recall_audit] cells=5" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_rank6_local_rescue_recall_audit] stop_condition=queue_exhausted_or_wallclock_budget_reached_or_first_cell_projection_over_budget" | Tee-Object -FilePath $LogRelPath -Append

py -3 $ScriptRelPath 2>&1 | Tee-Object -FilePath $LogRelPath -Append
$ExitCode = $LASTEXITCODE

"[stage35_rank6_local_rescue_recall_audit] exit_code=$ExitCode" | Tee-Object -FilePath $LogRelPath -Append
exit $ExitCode
