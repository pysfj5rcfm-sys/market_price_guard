param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('tech', 'energy')]
    [string]$Account
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$UnixPython = Join-Path $ProjectRoot '.venv/bin/python'
$HomeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $env:HOME }
$BundledPython = if ($HomeDir) { Join-Path $HomeDir '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' } else { '' }
$BundledUnixPython = if ($HomeDir) { Join-Path $HomeDir '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3' } else { '' }
$OutputDir = 'outputs_config_check_latest'

if (Test-Path $Python) {
    $null = & $Python --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Venv python could not start. Trying bundled/runtime Python.'
        $Python = ''
    }
} else {
    $Python = ''
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
            Write-Host 'Program error: Python not found. Please create .venv or install Python.'
            exit 1
        }
        $Python = $PathPython.Source
    }
}

Write-Host ('check: account layer config')
Write-Host ('account: ' + $Account)
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
& $Python -m market_price_guard.check_account_layer_config --account $Account --output-dir $OutputDir
$ExitCode = $LASTEXITCODE
if ($PreviousPythonPath) {
    $env:PYTHONPATH = $PreviousPythonPath
} else {
    Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
}
Pop-Location

Write-Host ('exit code: ' + $ExitCode)
exit $ExitCode
