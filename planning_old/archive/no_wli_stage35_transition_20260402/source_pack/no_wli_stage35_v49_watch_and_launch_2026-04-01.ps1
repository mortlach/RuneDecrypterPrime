$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$configPath = Join-Path $repoRoot "tools\benchmarks\periodic_sub_trans\no_wli\fixture_matrix_config.py"
$canaryStatePath = Join-Path $repoRoot "output\tools\benchmarks\periodic_sub_trans\no_wli\fixture_matrix_run_state_tune_v49_p9c3_seed411_stage35_baseline_selector_canary_reduced_2job.json"
$canaryEventsPath = Join-Path $repoRoot "output\tools\benchmarks\periodic_sub_trans\no_wli\fixture_matrix_run_events_tune_v49_p9c3_seed411_stage35_baseline_selector_canary_reduced_2job.jsonl"
$watchLogPath = Join-Path $repoRoot "planning\working\no_wli_stage35_v49_watch_2026-04-01.log"
$overnightConsoleLogPath = Join-Path $repoRoot "planning\working\no_wli_stage35_v48_overnight_console_2026-04-01.log"

function Write-WatchLog {
    param(
        [string]$Message
    )

    $line = "[{0}] {1}" -f (Get-Date -Format o), $Message
    Add-Content -LiteralPath $watchLogPath -Value $line -Encoding UTF8
}

function Read-JsonFile {
    param(
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $null
    }
    return ($raw | ConvertFrom-Json)
}

function Read-JsonLines {
    param(
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return @()
    }
    $rows = @()
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $rows += ($line | ConvertFrom-Json)
    }
    return $rows
}

function Test-CanaryPassed {
    param(
        [psobject]$State,
        [object[]]$Events
    )

    if ($null -eq $State) {
        return $false
    }
    if ([int]$State.completed_jobs -lt 2) {
        return $false
    }
    if ([int]$State.remaining_jobs -ne 0) {
        return $false
    }
    if ([int]$State.stopped_early -ne 0) {
        return $false
    }
    $jobErrors = @($Events | Where-Object { $_.event -eq "job_error" })
    if ($jobErrors.Count -gt 0) {
        return $false
    }
    return $true
}

function Test-CanaryFailed {
    param(
        [psobject]$State,
        [object[]]$Events
    )

    $jobErrors = @($Events | Where-Object { $_.event -eq "job_error" })
    if ($jobErrors.Count -gt 0) {
        return $true
    }
    if ($null -ne $State -and [int]$State.stopped_early -ne 0) {
        return $true
    }
    return $false
}

function Switch-ConfigToOvernight {
    $content = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8
    $updated = $content -replace 'STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "canary"', 'STAGE35_BASELINE_SELECTOR_COMPARE_MODE = "overnight"'
    if ($updated -eq $content) {
        throw "Could not switch fixture_matrix_config.py from canary to overnight."
    }
    Set-Content -LiteralPath $configPath -Value $updated -Encoding UTF8
}

function Start-OvernightRun {
    $command = "& 'C:\Python\Python311\python.exe' 'tools\benchmarks\periodic_sub_trans\no_wli\run_fixture_matrix.py' 2>&1 | Tee-Object -FilePath 'planning\working\no_wli_stage35_v48_overnight_console_2026-04-01.log'"
    Start-Process powershell `
        -WorkingDirectory $repoRoot `
        -ArgumentList @('-NoExit', '-Command', $command)
}

Write-WatchLog "watcher armed; monitoring v49 canary until clean completion or failure"

while ($true) {
    $state = Read-JsonFile -Path $canaryStatePath
    $events = Read-JsonLines -Path $canaryEventsPath

    if (Test-CanaryPassed -State $state -Events $events) {
        Write-WatchLog "v49 canary passed; switching config to overnight and launching v48 compare"
        Switch-ConfigToOvernight
        Start-OvernightRun
        Write-WatchLog "overnight v48 launch command started; console log path=planning\\working\\no_wli_stage35_v48_overnight_console_2026-04-01.log"
        break
    }

    if (Test-CanaryFailed -State $state -Events $events) {
        Write-WatchLog "v49 canary failed or stopped early; overnight launch canceled"
        break
    }

    Start-Sleep -Seconds 30
}
