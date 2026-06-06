$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
Set-Location $RepoRoot

$LogDir = 'output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_full80_remaining_batches_1_3_serial_v1'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$Log = Join-Path $LogDir 'strict_full80_remaining_batches_1_3_2026-06-06.log'
$Script = 'tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_remaining_batches_1_3_serial_v1.py'

"[s3_strict_remaining_batches_1_3] started_utc=$((Get-Date).ToUniversalTime().ToString('o'))" | Tee-Object -FilePath $Log -Append
"[s3_strict_remaining_batches_1_3] repo_root=$RepoRoot" | Tee-Object -FilePath $Log -Append
if (-not (Test-Path -LiteralPath $Script)) {
    "[s3_strict_remaining_batches_1_3] preflight_missing_script=$Script" | Tee-Object -FilePath $Log -Append
    exit 2
}
"[s3_strict_remaining_batches_1_3] preflight_script_path_ok=true" | Tee-Object -FilePath $Log -Append
& 'C:\Python\Python311\python.exe' $Script 2>&1 | Tee-Object -FilePath $Log -Append
if ($LASTEXITCODE -ne 0) {
    "[s3_strict_remaining_batches_1_3] failed exit_code=$LASTEXITCODE utc=$((Get-Date).ToUniversalTime().ToString('o'))" | Tee-Object -FilePath $Log -Append
    exit $LASTEXITCODE
}
"[s3_strict_remaining_batches_1_3] finished_utc=$((Get-Date).ToUniversalTime().ToString('o'))" | Tee-Object -FilePath $Log -Append
