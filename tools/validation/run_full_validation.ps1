$ErrorActionPreference = "Stop"

# Configure the external evidence directory before launching this script.
$ConfiguredOutputRoot = $env:RDP_VALIDATION_OUTPUT_ROOT
if ([string]::IsNullOrWhiteSpace($ConfiguredOutputRoot)) {
    throw "RDP_VALIDATION_OUTPUT_ROOT must name an external validation folder."
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$SiblingPython = Join-Path $RepoRoot "..\environment\Scripts\python.exe"
if (Test-Path -LiteralPath $SiblingPython) {
    $PythonExecutable = (Resolve-Path -LiteralPath $SiblingPython).Path
} else {
    $PythonExecutable = (Get-Command python -ErrorAction Stop).Source
}

$EvidenceRoot = [System.IO.Path]::GetFullPath($ConfiguredOutputRoot)
$RunnerOutputRoot = Join-Path $EvidenceRoot "runner_output"
$ConsoleLog = Join-Path $EvidenceRoot "full_validation_console.log"
New-Item -ItemType Directory -Path $RunnerOutputRoot -Force | Out-Null

$env:RDP_OUTPUT_ROOT = $RunnerOutputRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $Utf8NoBom
[Console]::OutputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom

$Writer = New-Object System.IO.StreamWriter($ConsoleLog, $false, $Utf8NoBom)
$ExitCode = 1
try {
    $Header = @(
        "RDP full validation",
        "Repository: $RepoRoot",
        "Python: $PythonExecutable",
        "Evidence root: $RunnerOutputRoot",
        "Console log: $ConsoleLog",
        "Started UTC: $([DateTime]::UtcNow.ToString('o'))"
    )
    foreach ($Line in $Header) {
        Write-Host $Line
        $Writer.WriteLine($Line)
    }
    $Writer.Flush()

    $PreviousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $PythonExecutable -X utf8 -u (Join-Path $RepoRoot "tools\run_validation.py") 2>&1 |
        ForEach-Object {
            $Line = $_.ToString()
            Write-Host $Line
            $Writer.WriteLine($Line)
            $Writer.Flush()
        }
    $ExitCode = $LASTEXITCODE
    $ErrorActionPreference = $PreviousErrorActionPreference
} finally {
    $Footer = "Validation process exited with code $ExitCode."
    Write-Host $Footer
    $Writer.WriteLine($Footer)
    $Writer.Flush()
    $Writer.Dispose()
}

Write-Host "Persistent console log: $ConsoleLog"
Read-Host "Press Enter to close this window"
exit $ExitCode
