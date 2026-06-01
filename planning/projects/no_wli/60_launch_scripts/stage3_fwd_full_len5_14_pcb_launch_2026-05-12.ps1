$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
Set-Location $RepoRoot

$LogPath = "output/logs/stage3_fwd_full_len5_14_pcb_run.log"
New-Item -ItemType Directory -Force -Path (Split-Path $LogPath) | Out-Null

python "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_runeberg_nose_stage3_len5_14_pcb.py" 2>&1 |
    Tee-Object -FilePath $LogPath -Append
