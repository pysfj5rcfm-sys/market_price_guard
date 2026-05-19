[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$OutputDir = 'outputs_mock_latest'
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

Write-Host 'profile: all'
Write-Host 'provider-policy: fast'
Write-Host ('output-dir: ' + $OutputDir)

Push-Location $ProjectRoot
& $Python -m market_price_guard.main --provider-mode mock --strict --output-dir $OutputDir
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
