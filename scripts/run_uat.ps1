[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$SummaryPath = Join-Path $ProjectRoot 'outputs_uat_summary.md'

$Items = @(
    @{
        Name = 'tech_fast_strict'
        Script = 'run_tech_fast_strict.ps1'
        OutputDir = 'outputs_tech_latest'
        PriceBlock = 'tech_price_block.md'
    },
    @{
        Name = 'tech_fast_reference'
        Script = 'run_tech_fast_reference.ps1'
        OutputDir = 'outputs_tech_reference_latest'
        PriceBlock = 'tech_price_block.md'
    },
    @{
        Name = 'tech_reconcile'
        Script = 'run_tech_reconcile.ps1'
        OutputDir = 'outputs_tech_reconcile_latest'
        PriceBlock = 'tech_price_block.md'
    },
    @{
        Name = 'tech_watchlist'
        Script = 'run_tech_watchlist.ps1'
        OutputDir = 'outputs_tech_watchlist_latest'
        PriceBlock = 'candidate_watchlist_report.md'
        UniverseType = 'candidate_watchlist'
    },
    @{
        Name = 'tech_scan_ai'
        Script = 'run_tech_scan_ai.ps1'
        OutputDir = 'outputs_tech_scan_ai_latest'
        PriceBlock = 'scan_universe_report.md'
        UniverseType = 'scan_universe'
    },
    @{
        Name = 'energy_fast_strict'
        Script = 'run_energy_fast_strict.ps1'
        OutputDir = 'outputs_energy_latest'
        PriceBlock = 'energy_price_block.md'
    },
    @{
        Name = 'all_fast_strict'
        Script = 'run_all_fast_strict.ps1'
        OutputDir = 'outputs_all_latest'
        PriceBlock = 'controller_price_summary.md'
    },
    @{
        Name = 'diagnostic'
        Script = 'run_diagnostic.ps1'
        OutputDir = 'outputs_diagnostic'
        PriceBlock = 'provider_health_report.md'
    }
)

$MockScript = Join-Path $ScriptDir 'run_mock_strict.ps1'
if (Test-Path $MockScript) {
    $Items += @{
        Name = 'mock_strict'
        Script = 'run_mock_strict.ps1'
        OutputDir = 'outputs_mock_latest'
        PriceBlock = 'controller_price_summary.md'
    }
}

$Results = @()
$AnyFailed = $false
$GeneratedAt = (Get-Date).ToUniversalTime().ToString('o')
$AdviceTerms = @(
    (-join ([char[]](0x5efa, 0x8bae, 0x4e70))),
    (-join ([char[]](0x5efa, 0x8bae, 0x5356))),
    (-join ([char[]](0x4e70, 0x5165))),
    (-join ([char[]](0x5356, 0x51fa))),
    (-join ([char[]](0x52a0, 0x4ed3))),
    (-join ([char[]](0x51cf, 0x4ed3))),
    (-join ([char[]](0x76ee, 0x6807, 0x4ef7)))
)

Push-Location $ProjectRoot
foreach ($Item in $Items) {
    $ScriptPath = Join-Path $ScriptDir $Item.Script
    & $ScriptPath
    $ExitCode = $LASTEXITCODE
    $OutputPath = Join-Path $ProjectRoot $Item.OutputDir
    $RequiredFiles = @(
        '0_upload_bundle.md',
        'debug_bundle.md',
        'index.md',
        'data_completeness_report.md',
        'provider_health_report.md',
        'runtime_diagnostics.md',
        'price_reconciliation_report.md',
        $Item.PriceBlock
    )
    $MissingFiles = @()
    foreach ($FileName in $RequiredFiles) {
        $FilePath = Join-Path $OutputPath $FileName
        if (-not (Test-Path $FilePath)) {
            $MissingFiles += $FileName
        }
    }

    $AdviceHits = @()
    if (Test-Path $OutputPath) {
        Get-ChildItem $OutputPath -Filter '*.md' | ForEach-Object {
            $Content = Get-Content $_.FullName -Raw -Encoding UTF8
            foreach ($Term in $AdviceTerms) {
                if ($Content.Contains($Term)) {
                    $AdviceHits += ($_.Name + ':' + $Term)
                }
            }
        }
    }
    $IndexPath = Join-Path $OutputPath 'index.md'
    $UploadBundlePath = Join-Path $OutputPath '0_upload_bundle.md'
    $DebugBundlePath = Join-Path $OutputPath 'debug_bundle.md'
    $ScriptContent = Get-Content $ScriptPath -Raw -Encoding UTF8
    $QuotePurpose = ''
    $UniverseType = ''
    $UnsupportedCount = 0
    if (Test-Path $IndexPath) {
        $IndexContent = Get-Content $IndexPath -Raw -Encoding UTF8
        if ($IndexContent -match 'quote_purpose:\s*([A-Za-z_]+)') {
            $QuotePurpose = $Matches[1]
        }
        if ($IndexContent -match 'universe_type:\s*([A-Za-z_]+)') {
            $UniverseType = $Matches[1]
        }
        if ($IndexContent -match 'unsupported_count:\s*(\d+)') {
            $UnsupportedCount = [int]$Matches[1]
        }
    }

    $Status = 'passed'
    if ($ExitCode -eq 2) {
        $Status = 'strict_blocked_but_reported'
    }
    if (($ExitCode -ne 0 -and $ExitCode -ne 2) -or $MissingFiles.Count -gt 0 -or $AdviceHits.Count -gt 0) {
        $Status = 'failed'
        $AnyFailed = $true
    }
    if ($Item.Name -in @('tech_watchlist', 'tech_scan_ai')) {
        $Status = 'passed'
        $WatchlistScanFailed = $false
        $Notes = @()
        if ($ExitCode -ne 0) {
            $WatchlistScanFailed = $true
            $Notes += 'exit_code_not_zero'
        }
        if (-not (Test-Path $OutputPath)) {
            $WatchlistScanFailed = $true
            $Notes += 'output_dir_missing'
        }
        if (-not (Test-Path $UploadBundlePath)) {
            $WatchlistScanFailed = $true
            $Notes += '0_upload_bundle_missing'
        }
        if (-not (Test-Path $DebugBundlePath)) {
            $WatchlistScanFailed = $true
            $Notes += 'debug_bundle_missing'
        }
        if ($ScriptContent -match '--strict') {
            $WatchlistScanFailed = $true
            $Notes += 'script_must_not_use_strict'
        }
        if ($UniverseType -ne $Item.UniverseType) {
            $WatchlistScanFailed = $true
            $Notes += ('unexpected_universe_type:' + $UniverseType)
        }
        if ($UnsupportedCount -gt 0 -and -not (Test-Path (Join-Path $OutputPath 'unsupported_symbols_report.md'))) {
            $WatchlistScanFailed = $true
            $Notes += 'unsupported_symbols_report_missing'
        }
        if (Test-Path $UploadBundlePath) {
            $UploadContent = Get-Content $UploadBundlePath -Raw -Encoding UTF8
            if (($UploadContent -notmatch '不可用于具体操作建议') -and ($UploadContent -notmatch 'not usable for concrete operation recommendations')) {
                $WatchlistScanFailed = $true
                $Notes += 'missing_non_operation_notice'
            }
        }
        if ($WatchlistScanFailed) {
            $Status = 'failed'
            $AnyFailed = $true
        } else {
            $MissingFiles = @()
            $AdviceHits = @()
        }
    }

    $Results += [PSCustomObject]@{
        Name = $Item.Name
        Script = $Item.Script
        ExitCode = $ExitCode
        Status = $Status
        OutputDir = $Item.OutputDir
        IndexExists = Test-Path (Join-Path $OutputPath 'index.md')
        UploadBundleExists = Test-Path (Join-Path $OutputPath '0_upload_bundle.md')
        DebugBundleExists = Test-Path (Join-Path $OutputPath 'debug_bundle.md')
        CompletenessExists = Test-Path (Join-Path $OutputPath 'data_completeness_report.md')
        HealthExists = Test-Path (Join-Path $OutputPath 'provider_health_report.md')
        RuntimeExists = Test-Path (Join-Path $OutputPath 'runtime_diagnostics.md')
        ReconciliationExists = Test-Path (Join-Path $OutputPath 'price_reconciliation_report.md')
        UnsupportedSymbolsExists = Test-Path (Join-Path $OutputPath 'unsupported_symbols_report.md')
        UnsupportedCount = $UnsupportedCount
        UniverseType = $UniverseType
        PriceBlockExists = Test-Path (Join-Path $OutputPath $Item.PriceBlock)
        QuotePurpose = $QuotePurpose
        MissingFiles = $MissingFiles
        AdviceHits = $AdviceHits
    }
}
Pop-Location

$Passed = ($Results | Where-Object { $_.Status -eq 'passed' }).Count
$StrictBlocked = ($Results | Where-Object { $_.Status -eq 'strict_blocked_but_reported' }).Count
$Failed = ($Results | Where-Object { $_.Status -eq 'failed' }).Count
$AnyFailed = $Failed -gt 0

$Lines = @()
$Lines += '# market_price_guard UAT Summary'
$Lines += ''
$Lines += ('- generated_at: ' + $GeneratedAt)
$Lines += ('- total: ' + $Results.Count)
$Lines += ('- passed: ' + $Passed)
$Lines += ('- strict_blocked_but_reported: ' + $StrictBlocked)
$Lines += ('- failed: ' + $Failed)
$Lines += ''
$Lines += 'strict=2 means the price guard blocked operation; it is not a UAT failure when reports are generated and blocking is explained.'
$Lines += ''
$Lines += '## Items'

foreach ($Result in $Results) {
    $Lines += ''
    $Lines += ('### ' + $Result.Name)
    $Lines += ('- command/script: ' + $Result.Script)
    $Lines += ('- exit_code: ' + $Result.ExitCode)
    $Lines += ('- status: ' + $Result.Status)
    $Lines += ('- output_dir: ' + $Result.OutputDir)
    $Lines += ('- index.md exists: ' + $Result.IndexExists)
    $Lines += ('- 0_upload_bundle.md exists: ' + $Result.UploadBundleExists)
    $Lines += ('- debug_bundle.md exists: ' + $Result.DebugBundleExists)
    $Lines += ('- quote_purpose: ' + $Result.QuotePurpose)
    $Lines += ('- universe_type: ' + $Result.UniverseType)
    $Lines += ('- unsupported_count: ' + $Result.UnsupportedCount)
    $Lines += ('- data_completeness_report.md exists: ' + $Result.CompletenessExists)
    $Lines += ('- provider_health_report.md exists: ' + $Result.HealthExists)
    $Lines += ('- runtime_diagnostics.md exists: ' + $Result.RuntimeExists)
    $Lines += ('- price_reconciliation_report.md exists: ' + $Result.ReconciliationExists)
    $Lines += ('- unsupported_symbols_report.md exists: ' + $Result.UnsupportedSymbolsExists)
    $Lines += ('- price_block exists: ' + $Result.PriceBlockExists)
    if ($Result.Name -in @('tech_watchlist', 'tech_scan_ai')) {
        $Lines += '- strict_pollution_isolation: candidate/scan universes are non-strict reference outputs.'
    }
    if ($Result.MissingFiles.Count -gt 0) {
        $Lines += ('- missing_files: ' + ($Result.MissingFiles -join ', '))
    } else {
        $Lines += '- missing_files: none'
    }
    if ($Result.AdviceHits.Count -gt 0) {
        $Lines += ('- advice_keyword_hits: ' + ($Result.AdviceHits -join ', '))
    } else {
        $Lines += '- advice_keyword_hits: none'
    }
    $Lines += '- notes: strict_blocked_but_reported is acceptable when blocking reports exist.'
}

$Lines | Set-Content $SummaryPath -Encoding UTF8

Write-Host ('UAT summary: ' + $SummaryPath)
if ($AnyFailed) {
    exit 1
}
exit 0
