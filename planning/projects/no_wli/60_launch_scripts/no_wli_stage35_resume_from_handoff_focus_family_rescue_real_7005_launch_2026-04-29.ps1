$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..\..\..")
Set-Location $RepoRoot

$Python = "C:\Python\Python311\python.exe"
$Runner = "tools\benchmarks\periodic_sub_trans\no_wli\analysis\fixed_instance_solver_development_v1\run_stage35_resume_from_handoff_focus_family_rescue_real_7005_v1.py"
$LogDir = "planning\projects\no_wli\50_console_and_watch_logs"
$LogPath = Join-Path $LogDir "no_wli_stage35_resume_from_handoff_focus_family_rescue_real_7005_2026-04-29.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Host "Repo root: $RepoRoot"
Write-Host "Runner: $Runner"
Write-Host "Log: $LogPath"
Write-Host "Natural stop: one bounded Stage 3.5 round; no runtime cap."
Write-Host "Started UTC: $((Get-Date).ToUniversalTime().ToString('o'))"

& $Python $Runner 2>&1 | Tee-Object -FilePath $LogPath -Append
$ExitCode = $LASTEXITCODE

Write-Host "Finished UTC: $((Get-Date).ToUniversalTime().ToString('o'))"
Write-Host "Exit code: $ExitCode"
exit $ExitCode
