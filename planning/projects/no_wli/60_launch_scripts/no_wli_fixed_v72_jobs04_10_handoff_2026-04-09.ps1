$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path "."
Set-Location $repoRoot

$configPath = "tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py"
$watchLogPath = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_fixed_v72_jobs04_10_handoff_2026-04-09.log"
$consoleLogPathA = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_fixed_v72a_jobs04_05_2026-04-09.log"
$consoleLogPathB = "planning/projects/no_wli/50_console_and_watch_logs/no_wli_fixed_v72b_jobs06_10_2026-04-09.log"
$pythonExe = "C:\Python\Python311\python.exe"

function Write-WatchLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
    $line = "[$timestamp] $Message"
    Add-Content -LiteralPath $watchLogPath -Value $line -Encoding UTF8
}

function Invoke-FixedProfileRun {
    param(
        [string]$OriginalConfig,
        [string]$ProfileName,
        [string]$ConsoleLogPath,
        [string]$RunLabel
    )

    $updatedConfig = $OriginalConfig -replace 'FIXED_INSTANCE_EXECUTION_PROFILE = "off"', ('FIXED_INSTANCE_EXECUTION_PROFILE = "' + $ProfileName + '"')
    if ($updatedConfig -eq $OriginalConfig) {
        throw "Failed to switch FIXED_INSTANCE_EXECUTION_PROFILE to $ProfileName"
    }

    Set-Content -LiteralPath $configPath -Value $updatedConfig -Encoding UTF8
    Write-WatchLog "config switched to $ProfileName; launching $RunLabel"
    & $pythonExe "tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py" *>> $ConsoleLogPath
    $exitCode = $LASTEXITCODE
    Write-WatchLog "$RunLabel finished with exit code $exitCode"
    if ($exitCode -ne 0) {
        throw "$RunLabel failed with exit code $exitCode"
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path $watchLogPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $consoleLogPathA) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $consoleLogPathB) | Out-Null

$originalConfig = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8
if ($originalConfig -notmatch 'FIXED_INSTANCE_EXECUTION_PROFILE = "off"') {
    throw "Expected safe checked-in fixed-instance profile to be off before v72 handoff launch"
}

$exitCode = 1
try {
    Write-WatchLog "starting exact handoff package for original v71 jobs 4-10"
    Invoke-FixedProfileRun -OriginalConfig $originalConfig -ProfileName "panel_v1_jobs04_05" -ConsoleLogPath $consoleLogPathA -RunLabel "v72a jobs04_05"
    Invoke-FixedProfileRun -OriginalConfig $originalConfig -ProfileName "panel_v1_jobs06_10" -ConsoleLogPath $consoleLogPathB -RunLabel "v72b jobs06_10"
    $exitCode = 0
    Write-WatchLog "v72 exact handoff package completed cleanly"
}
finally {
    Set-Content -LiteralPath $configPath -Value $originalConfig -Encoding UTF8
    Write-WatchLog "config restored to safe off profile"
}

exit $exitCode

