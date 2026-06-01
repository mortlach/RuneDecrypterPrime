$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..\..\..")
$LaunchScript = Join-Path $RepoRoot "planning\projects\no_wli\60_launch_scripts\no_wli_stage35_resume_from_handoff_focus_family_rescue_real_7005_launch_2026-04-29.ps1"

Start-Process powershell.exe -WindowStyle Normal -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $LaunchScript
)
