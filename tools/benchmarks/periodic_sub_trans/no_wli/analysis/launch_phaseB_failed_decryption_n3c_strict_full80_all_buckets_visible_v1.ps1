$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../..')).Path
Set-Location $RepoRoot

$LogDir = 'output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_failed_decryption_n3c_strict_full80_all_buckets_visible_v1'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$Log = Join-Path $LogDir 'strict_full80_all_buckets_2026-06-05.log'

$Scripts = @(
    'tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_8_9_query_evidence_v1.py',
    'tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_10_11_query_evidence_v1.py',
    'tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_12_14_query_evidence_v1.py',
    'tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_15_17_query_evidence_v1.py',
    'tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_failed_decryption_n3c_strict_full80_bucket_18_plus_query_evidence_v1.py'
)

"[s3_strict_full80_serial] started_utc=$((Get-Date).ToUniversalTime().ToString('o'))" | Tee-Object -FilePath $Log -Append
"[s3_strict_full80_serial] repo_root=$RepoRoot" | Tee-Object -FilePath $Log -Append
foreach ($Script in $Scripts) {
    if (-not (Test-Path -LiteralPath $Script)) {
        "[s3_strict_full80_serial] preflight_missing_script=$Script" | Tee-Object -FilePath $Log -Append
        exit 2
    }
}
"[s3_strict_full80_serial] preflight_script_paths_ok=true" | Tee-Object -FilePath $Log -Append
foreach ($Script in $Scripts) {
    "[s3_strict_full80_serial] launching $Script utc=$((Get-Date).ToUniversalTime().ToString('o'))" | Tee-Object -FilePath $Log -Append
    & 'C:\Python\Python311\python.exe' $Script 2>&1 | Tee-Object -FilePath $Log -Append
    if ($LASTEXITCODE -ne 0) {
        "[s3_strict_full80_serial] failed script=$Script exit_code=$LASTEXITCODE utc=$((Get-Date).ToUniversalTime().ToString('o'))" | Tee-Object -FilePath $Log -Append
        exit $LASTEXITCODE
    }
    "[s3_strict_full80_serial] completed $Script utc=$((Get-Date).ToUniversalTime().ToString('o'))" | Tee-Object -FilePath $Log -Append
}
"[s3_strict_full80_serial] finished_utc=$((Get-Date).ToUniversalTime().ToString('o'))" | Tee-Object -FilePath $Log -Append
