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
$UnixPython = Join-Path $ProjectRoot '.venv/bin/python'
$HomeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $env:HOME }
$BundledPython = if ($HomeDir) { Join-Path $HomeDir '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' } else { '' }
$BundledUnixPython = if ($HomeDir) { Join-Path $HomeDir '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3' } else { '' }
$OutputDir = 'outputs_tech_minute_probe_latest'
$IndexPath = Join-Path $ProjectRoot ($OutputDir + '\index.md')

if (-not (Test-Path $Python)) {
    $Python = ''
}

if ($Python) {
    $null = & $Python --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Venv python could not start. Trying bundled/runtime Python.'
        $Python = ''
    }
}
if (-not $Python) {
    if (Test-Path $UnixPython) {
        $Python = $UnixPython
    } elseif ($BundledPython -and (Test-Path $BundledPython)) {
        $Python = $BundledPython
    } elseif ($BundledUnixPython -and (Test-Path $BundledUnixPython)) {
        $Python = $BundledUnixPython
    } else {
        $PathPython = Get-Command python -ErrorAction SilentlyContinue
        if ($null -eq $PathPython) {
            $PathPython = Get-Command python3 -ErrorAction SilentlyContinue
        }
        if ($null -eq $PathPython) {
            $PathPython = Get-Command py -ErrorAction SilentlyContinue
        }
        if ($null -eq $PathPython) {
            Write-Host 'Program error: fallback python launcher not found on PATH.'
            exit 1
        }
        $Python = $PathPython.Source
    }
}

Write-Host 'profile: tech'
Write-Host 'provider-policy: fast'
Write-Host 'quote-purpose: reference'
Write-Host 'minute-bars-probe: enabled'
Write-Host ('minute-mode: ' + $Mode)
Write-Host ('minute-workers: ' + $MinuteWorkers)
Write-Host ('output-dir: ' + $OutputDir)

Push-Location $ProjectRoot
$PreviousPythonPath = $env:PYTHONPATH
$SrcPath = Join-Path $ProjectRoot 'src'
$VenvSitePackages = Join-Path $ProjectRoot '.venv\Lib\site-packages'
$BundledSitePackages = Join-Path (Split-Path -Parent $Python) 'Lib\site-packages'
$PythonPathParts = @($SrcPath)
if (Test-Path $BundledSitePackages) {
    $PythonPathParts += $BundledSitePackages
}
if (Test-Path $VenvSitePackages) {
    $PythonPathParts += $VenvSitePackages
}
if ($PreviousPythonPath) {
    $PythonPathParts += $PreviousPythonPath
}
$env:PYTHONPATH = ($PythonPathParts -join [System.IO.Path]::PathSeparator)
& $Python -m market_price_guard.main --profile tech --provider-mode live --provider-policy fast --quote-purpose reference --include-minute-bars --minute-mode $Mode --minute-workers $MinuteWorkers --output-dir outputs_tech_minute_probe_latest
$ExitCode = $LASTEXITCODE
if ($PreviousPythonPath) {
    $env:PYTHONPATH = $PreviousPythonPath
} else {
    Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
}
Pop-Location

Write-Host ('exit code: ' + $ExitCode)
Write-Host ('index.md: ' + $IndexPath)
if ($ExitCode -eq 2) {
    Write-Host ('Strict blocked: see ' + $OutputDir + '/index.md')
} elseif ($ExitCode -ne 0) {
    Write-Host 'Program error: see console output.'
}

exit $ExitCode
