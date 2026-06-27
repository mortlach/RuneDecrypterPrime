param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsFromCaller
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallPy = Join-Path $ScriptDir "install.py"

Write-Host "Rune Decrypter Prime V1 full installer"
Write-Host "This installs or verifies the required LM3/LM4 release assets."
Write-Host "If automatic download fails, place rdp-v1-lm-large-part*.zip under downloads/ and run this again."
Write-Host ""

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3.11 $InstallPy @ArgsFromCaller
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    python $InstallPy @ArgsFromCaller
    exit $LASTEXITCODE
}

Write-Error "Python launcher not found. Install Python 3.11+ and retry."
exit 1
