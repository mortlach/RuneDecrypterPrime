$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
Set-Location $RepoRoot

$LaunchScriptPath = Join-Path $PSScriptRoot "no_wli_phaseb_challenger_supply_matrix_launch_2026-04-19.ps1"

Start-Process powershell -WorkingDirectory $RepoRoot.Path -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', $LaunchScriptPath
