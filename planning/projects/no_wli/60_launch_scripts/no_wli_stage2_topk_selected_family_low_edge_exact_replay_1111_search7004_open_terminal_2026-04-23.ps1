$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..\..")).Path
$launchScript = (Resolve-Path (Join-Path $scriptDir "no_wli_stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_launch_2026-04-23.ps1")).Path

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $launchScript
) -WorkingDirectory $repoRoot
