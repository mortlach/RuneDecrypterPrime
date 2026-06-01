$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..\..")).Path
$launchScript = (Resolve-Path (Join-Path $scriptDir "no_wli_stage3_entry_const_local_depth_fixed_canary_launch_2026-04-22.ps1")).Path

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $launchScript
) -WorkingDirectory $repoRoot
