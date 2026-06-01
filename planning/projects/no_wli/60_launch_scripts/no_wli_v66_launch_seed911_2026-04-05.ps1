$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$ConsoleLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_v66_seed911_console_2026-04-05.log"

Set-Location $RepoRoot

"$((Get-Date).ToUniversalTime().ToString('o')) [v66-launch] repo_root=$RepoRoot" |
    Tee-Object -FilePath $ConsoleLogPath -Append
"$((Get-Date).ToUniversalTime().ToString('o')) [v66-launch] mode=candidate_single_p9_seed911" |
    Tee-Object -FilePath $ConsoleLogPath -Append

C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py 2>&1 |
    Tee-Object -FilePath $ConsoleLogPath -Append

