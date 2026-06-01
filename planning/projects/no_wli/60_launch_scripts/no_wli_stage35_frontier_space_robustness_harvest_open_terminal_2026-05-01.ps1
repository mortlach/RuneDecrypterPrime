$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
Set-Location $RepoRoot

$LaunchRelPath = "planning/projects/no_wli/60_launch_scripts/no_wli_stage35_frontier_space_robustness_harvest_launch_2026-05-01.ps1"

Start-Process powershell.exe -WorkingDirectory $RepoRoot -WindowStyle Normal -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $LaunchRelPath
)
