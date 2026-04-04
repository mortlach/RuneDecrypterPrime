@echo off
setlocal
cd /d "%~dp0..\..\..\.."
C:\Python\Python311\python.exe tools\benchmarks\periodic_sub_trans\no_wli\run_fixture_matrix.py > output\tools\benchmarks\periodic_sub_trans\no_wli\fixture_matrix_run_v23_stdout.log 2> output\tools\benchmarks\periodic_sub_trans\no_wli\fixture_matrix_run_v23_stderr.log
endlocal
