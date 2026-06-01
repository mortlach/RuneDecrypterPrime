$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path "."
Set-Location $repoRoot

$targetPid = 44616
$configPath = "tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py"
$watchLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_fixed_v70_watch_and_launch_v71_2026-04-08.log"
$consoleLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_fixed_v71_panel_v1_long_2026-04-08.log"
$pythonExe = "C:\Python\Python311\python.exe"

function Write-WatchLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
    $line = "[$timestamp] $Message"
    Add-Content -LiteralPath $watchLogPath -Value $line -Encoding UTF8
}

New-Item -ItemType Directory -Force -Path (Split-Path $watchLogPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $consoleLogPath) | Out-Null

$originalConfig = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8
if ($originalConfig -notmatch 'FIXED_INSTANCE_EXECUTION_PROFILE = "off"') {
    throw "Expected safe checked-in fixed-instance profile to be off before watcher launch"
}

Write-WatchLog "watcher armed for PID $targetPid"
while ($null -ne (Get-Process -Id $targetPid -ErrorAction SilentlyContinue)) {
    Start-Sleep -Seconds 30
}
Write-WatchLog "target PID $targetPid exited; preparing v71 fixed long run"

$updatedConfig = $originalConfig -replace 'FIXED_INSTANCE_EXECUTION_PROFILE = "off"', 'FIXED_INSTANCE_EXECUTION_PROFILE = "panel_v1_long"'
if ($updatedConfig -eq $originalConfig) {
    throw "Failed to switch FIXED_INSTANCE_EXECUTION_PROFILE to panel_v1_long"
}

$exitCode = 1
try {
    Set-Content -LiteralPath $configPath -Value $updatedConfig -Encoding UTF8
    Write-WatchLog "config switched to panel_v1_long; launching v71"
    & $pythonExe "tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py" *>> $consoleLogPath
    $exitCode = $LASTEXITCODE
    Write-WatchLog "v71 finished with exit code $exitCode"
}
finally {
    Set-Content -LiteralPath $configPath -Value $originalConfig -Encoding UTF8
    Write-WatchLog "config restored to safe off profile"
}

exit $exitCode

