$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
Set-Location $RepoRoot

$LaunchScriptPath = Join-Path $PSScriptRoot "no_wli_phasec_richer_pool_replacement_reopen_launch_2026-04-21.ps1"

Start-Process powershell -WorkingDirectory $RepoRoot.Path -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', $LaunchScriptPath
