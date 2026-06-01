$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$ConsoleLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_v65_seed811_console_2026-04-05.log"

Set-Location $RepoRoot

"$((Get-Date).ToUniversalTime().ToString('o')) [v65-launch] repo_root=$RepoRoot" |
    Tee-Object -FilePath $ConsoleLogPath -Append
"$((Get-Date).ToUniversalTime().ToString('o')) [v65-launch] mode=candidate_single_p9_seed811" |
    Tee-Object -FilePath $ConsoleLogPath -Append

C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py 2>&1 |
    Tee-Object -FilePath $ConsoleLogPath -Append

