[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AccountScript = Join-Path $ScriptDir 'check_account_layer_config.ps1'

Write-Host 'check: tech layer config'
& $AccountScript -Account tech
$ExitCode = $LASTEXITCODE
exit $ExitCode
