$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
Set-Location $RepoRoot

$RunLabel = "candidate3_phasec_saved_surface_policy_seed_sweep_v1"
$PythonExe = "C:\Python\Python311\python.exe"
$PythonScriptPath = "tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/explore_phasec_saved_surface_policy_seed_sweep_v1.py"
$ConsoleLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_candidate3_phasec_saved_surface_policy_seed_sweep_2026-04-18.log"

function Write-ConsoleLog {
    param([string]$Message)
    $timestamp = (Get-Date).ToUniversalTime().ToString("o")
    "[$timestamp] $Message" | Tee-Object -FilePath $ConsoleLogPath -Append
}

New-Item -ItemType Directory -Force -Path (Split-Path $ConsoleLogPath) | Out-Null

Write-ConsoleLog "[$RunLabel] launch_started script=$PythonScriptPath"
& $PythonExe $PythonScriptPath 2>&1 | Tee-Object -FilePath $ConsoleLogPath -Append
$ExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
Write-ConsoleLog "[$RunLabel] launch_finished exit_code=$ExitCode"

exit $ExitCode
