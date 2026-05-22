param(
    [string]$Mode = 'balanced',
    [int]$MinuteWorkers = 3
)

# Usage: .\scripts\run_tech_minute_probe.ps1 -Mode balanced -MinuteWorkers 3
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

if ($Mode -notin @('fast', 'balanced', 'diagnostic')) {
    Write-Host 'Invalid Mode. Valid values: fast, balanced, diagnostic.'
    exit 1
}
if ($MinuteWorkers -lt 1) {
    Write-Host 'Invalid MinuteWorkers. Use an integer >= 1.'
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$OutputDir = 'outputs_tech_minute_probe_latest'
$IndexPath = Join-Path $ProjectRoot ($OutputDir + '\index.md')

if (-not (Test-Path $Python)) {
    Write-Host 'Venv not found: .venv\Scripts\python.exe. Please create .venv and install dependencies first.'
    exit 1
}

$null = & $Python --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Venv python could not start. Falling back to python on PATH.'
    $PathPython = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $PathPython) {
        $PathPython = Get-Command py -ErrorAction SilentlyContinue
    }
    if ($null -eq $PathPython) {
        Write-Host 'Program error: fallback python launcher not found on PATH.'
        exit 1
    }
    $Python = $PathPython.Source
}

Write-Host 'profile: tech'
Write-Host 'provider-policy: fast'
Write-Host 'quote-purpose: reference'
Write-Host 'minute-bars-probe: enabled'
Write-Host ('minute-mode: ' + $Mode)
Write-Host ('minute-workers: ' + $MinuteWorkers)
Write-Host ('output-dir: ' + $OutputDir)

Push-Location $ProjectRoot
& $Python -m market_price_guard.main --profile tech --provider-mode live --provider-policy fast --quote-purpose reference --include-minute-bars --minute-mode $Mode --minute-workers $MinuteWorkers --output-dir outputs_tech_minute_probe_latest
$ExitCode = $LASTEXITCODE
Pop-Location

Write-Host ('exit code: ' + $ExitCode)
Write-Host ('index.md: ' + $IndexPath)
if ($ExitCode -eq 2) {
    Write-Host ('Strict blocked: see ' + $OutputDir + '/index.md')
} elseif ($ExitCode -ne 0) {
    Write-Host 'Program error: see console output.'
}

exit $ExitCode
