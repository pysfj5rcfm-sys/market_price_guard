[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$BundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$OutputDir = 'outputs_tech_watchlist_latest'
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
    if (Test-Path $BundledPython) {
        $Python = $BundledPython
    } else {
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
}

Write-Host 'profile: tech'
Write-Host 'universe: tech_watchlist'
Write-Host 'provider-policy: fast'
Write-Host 'quote-purpose: reference'
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
& $Python -m market_price_guard.main --profile tech --universe tech_watchlist --provider-mode live --quote-purpose reference --provider-policy fast --output-dir outputs_tech_watchlist_latest
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
