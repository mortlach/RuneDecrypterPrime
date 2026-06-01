$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
Set-Location $RepoRoot

$LogRelPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_guard_relaxation_archive_policy_long_audit_2026-04-29.log"
$LogParent = Split-Path $LogRelPath -Parent
New-Item -ItemType Directory -Force -Path $LogParent | Out-Null

$env:PYTHONUNBUFFERED = "1"
$ScriptRelPath = "tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_guard_relaxation_archive_policy_long_audit_v1.py"

"[stage35_guard_relaxation_archive_policy_long_audit] repo=$((Get-Location).Path)" | Tee-Object -FilePath $LogRelPath
"[stage35_guard_relaxation_archive_policy_long_audit] script=$ScriptRelPath" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_guard_relaxation_archive_policy_long_audit] log=$LogRelPath" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_guard_relaxation_archive_policy_long_audit] max_wallclock_seconds=28800" | Tee-Object -FilePath $LogRelPath -Append
"[stage35_guard_relaxation_archive_policy_long_audit] stop_condition=all_discovered_stage35_archives_processed_or_wallclock_budget_reached" | Tee-Object -FilePath $LogRelPath -Append

py -3 $ScriptRelPath 2>&1 | Tee-Object -FilePath $LogRelPath -Append
$ExitCode = $LASTEXITCODE

"[stage35_guard_relaxation_archive_policy_long_audit] exit_code=$ExitCode" | Tee-Object -FilePath $LogRelPath -Append
exit $ExitCode
