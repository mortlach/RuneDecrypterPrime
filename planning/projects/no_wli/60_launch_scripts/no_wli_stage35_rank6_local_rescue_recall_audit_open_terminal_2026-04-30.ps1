$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
Set-Location $RepoRoot

$LaunchRelPath = "planning/projects/no_wli/60_launch_scripts/no_wli_stage35_rank6_local_rescue_recall_audit_launch_2026-04-30.ps1"

Start-Process powershell.exe -WorkingDirectory $RepoRoot -WindowStyle Normal -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $LaunchRelPath
)
