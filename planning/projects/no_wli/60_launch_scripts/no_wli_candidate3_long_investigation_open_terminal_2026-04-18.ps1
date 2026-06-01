$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
Set-Location $RepoRoot

$LaunchScriptPath = Join-Path $PSScriptRoot "no_wli_candidate3_long_investigation_launch_2026-04-18.ps1"

Start-Process powershell -WorkingDirectory $RepoRoot.Path -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', $LaunchScriptPath
