$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..\..")).Path
$queueScript = (Resolve-Path (Join-Path $scriptDir "no_wli_stage3_entry_const_local_depth_fixed_followon_1111_search7005_queue_after_v76_2026-04-22.ps1")).Path

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $queueScript
) -WorkingDirectory $repoRoot
