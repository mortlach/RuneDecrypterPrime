$ErrorActionPreference = "Stop"

$ConsoleLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_v57_p9_console_2026-04-02.log"

C:\Python\Python311\python.exe tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py `
    2>&1 | Tee-Object -FilePath $ConsoleLogPath

