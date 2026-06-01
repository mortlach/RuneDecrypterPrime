$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..\..")).Path
$launchScript = (Resolve-Path (Join-Path $scriptDir "no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_microbatch_launch_2026-04-24.ps1")).Path

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $launchScript
) -WorkingDirectory $repoRoot
