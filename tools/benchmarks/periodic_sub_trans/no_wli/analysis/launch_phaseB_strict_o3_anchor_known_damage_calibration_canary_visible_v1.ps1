$ErrorActionPreference = 'Stop'

$ScriptPath = $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path (Split-Path -Parent $ScriptPath) '..\..\..\..\..')).Path
Set-Location $RepoRoot

$Phase = 'phaseB_strict_o3_anchor_known_damage_calibration_canary_v2_fix'
$OutputDir = Join-Path $RepoRoot "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/$Phase"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$LogPath = Join-Path $OutputDir 'known_damage_calibration_canary_v2_fix_2026-06-07.log'
$Python = 'C:\Python\Python311\python.exe'
$Runner = 'tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_strict_o3_anchor_known_damage_calibration_canary_v1.py'

"[$Phase] repo_root=$RepoRoot" | Tee-Object -FilePath $LogPath
"[$Phase] started_utc=$((Get-Date).ToUniversalTime().ToString('o'))" | Tee-Object -FilePath $LogPath -Append
"[$Phase] wallclock_budget_seconds=10800" | Tee-Object -FilePath $LogPath -Append
"[$Phase] stop_condition=complete_774_runtime_chunks_or_10800_seconds" | Tee-Object -FilePath $LogPath -Append
"[$Phase] runner=$Runner" | Tee-Object -FilePath $LogPath -Append

& $Python $Runner 2>&1 | Tee-Object -FilePath $LogPath -Append
$ExitCode = $LASTEXITCODE

"[$Phase] finished_utc=$((Get-Date).ToUniversalTime().ToString('o'))" | Tee-Object -FilePath $LogPath -Append
"[$Phase] exit_code=$ExitCode" | Tee-Object -FilePath $LogPath -Append
exit $ExitCode
