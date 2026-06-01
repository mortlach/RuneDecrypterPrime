$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..")).Path
$launchScript = (Resolve-Path (Join-Path $scriptDir "no_wli_phaseb_challenger_supply_retake_microbatch_v1_launch_2026-04-20.ps1")).Path

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $launchScript
) -WorkingDirectory $repoRoot
