$ErrorActionPreference = "Stop"

$ConsoleLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_v59_ladder_small_console_2026-04-03.log"

C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py |
    Tee-Object -FilePath $ConsoleLogPath -Append

