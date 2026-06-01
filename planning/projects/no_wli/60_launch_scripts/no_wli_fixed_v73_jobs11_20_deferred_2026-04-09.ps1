$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path "."
Set-Location $repoRoot

$configPath = "tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py"
$watchLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_fixed_v73_jobs11_20_deferred_2026-04-09.log"
$consoleLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_fixed_v73_jobs11_20_2026-04-09.log"
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
    throw "Expected safe checked-in fixed-instance profile to be off before v73 deferred launch"
}

$updatedConfig = $originalConfig -replace 'FIXED_INSTANCE_EXECUTION_PROFILE = "off"', 'FIXED_INSTANCE_EXECUTION_PROFILE = "panel_v1_jobs11_20"'
if ($updatedConfig -eq $originalConfig) {
    throw "Failed to switch FIXED_INSTANCE_EXECUTION_PROFILE to panel_v1_jobs11_20"
}

$exitCode = 1
try {
    Set-Content -LiteralPath $configPath -Value $updatedConfig -Encoding UTF8
    Write-WatchLog "config switched to panel_v1_jobs11_20; launching v73 deferred jobs11_20 tail"
    & $pythonExe "tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py" *>> $consoleLogPath
    $exitCode = $LASTEXITCODE
    Write-WatchLog "v73 deferred jobs11_20 tail finished with exit code $exitCode"
}
finally {
    Set-Content -LiteralPath $configPath -Value $originalConfig -Encoding UTF8
    Write-WatchLog "config restored to safe off profile"
}

exit $exitCode

