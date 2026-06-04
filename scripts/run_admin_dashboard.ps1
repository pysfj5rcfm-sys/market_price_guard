param()

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$BundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'

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
    if (Test-Path $BundledPython) {
        $Python = $BundledPython
    } else {
        $PathPython = Get-Command python -ErrorAction SilentlyContinue
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

Write-Host 'market_price_guard local admin dashboard'
Write-Host 'Open: http://127.0.0.1:8766/admin'
& $Python -m market_price_guard.admin_app --host 127.0.0.1 --port 8766 --project-root $ProjectRoot
$ExitCode = $LASTEXITCODE

if ($PreviousPythonPath) {
    $env:PYTHONPATH = $PreviousPythonPath
} else {
    Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
}
Pop-Location
exit $ExitCode
