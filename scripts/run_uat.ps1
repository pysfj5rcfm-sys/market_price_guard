param(
    [string]$Mode = 'quick',
    [switch]$UseRunCache
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$SummaryPath = Join-Path $ProjectRoot 'outputs_uat_summary.md'
$RunCacheDir = Join-Path $ProjectRoot 'outputs_uat_run_cache_latest'

$AllowedModes = @('quick', 'intraday', 'full')
$Mode = $Mode.ToLowerInvariant()
if ($Mode -notin $AllowedModes) {
    Write-Host ('Invalid UAT mode: ' + $Mode)
    Write-Host 'Valid modes: quick, intraday, full'
    exit 1
}

$ModeItems = @{
    quick = @(
        'tech_fast_strict',
        'tech_operation_candidates',
        'tech_intraday_metrics',
        'mock_strict'
    )
    intraday = @(
        'tech_fast_strict',
        'tech_operation_candidates',
        'tech_minute_probe',
        'tech_intraday_metrics',
        'mock_strict'
    )
    full = @(
        'tech_fast_strict',
        'tech_fast_reference',
        'tech_reconcile',
        'tech_watchlist',
        'tech_scan_ai',
        'tech_operation_candidates',
        'tech_minute_probe',
        'tech_intraday_metrics',
        'energy_fast_strict',
        'all_fast_strict',
        'diagnostic',
        'mock_strict'
    )
}

$ModeExplanation = @{
    quick = 'quick mode skips heavy live provider diagnostics. Use -Mode full for complete regression.'
    intraday = 'intraday mode runs minute probe and reference intraday metrics without heavy reconcile/scan/diagnostic live sweeps.'
    full = 'full mode runs the complete live provider regression and can be slow.'
}

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
        Name = 'tech_operation_candidates'
        Script = 'run_tech_operation_candidates.ps1'
        OutputDir = 'outputs_tech_operation_candidates_latest'
        PriceBlock = 'operation_candidate_report.md'
        UniverseType = 'operation_candidate'
    },
    @{
        Name = 'tech_minute_probe'
        Script = 'run_tech_minute_probe.ps1'
        OutputDir = 'outputs_tech_minute_probe_latest'
        PriceBlock = 'provider_capability_report.md'
    },
    @{
        Name = 'tech_intraday_metrics'
        Script = 'run_tech_intraday_metrics.ps1'
        OutputDir = 'outputs_tech_intraday_latest'
        PriceBlock = 'reference_vwap_report.md'
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
$PreviousUseRunCache = $env:MARKET_GUARD_USE_UAT_RUN_CACHE
$PreviousRunCacheDir = $env:MARKET_GUARD_UAT_RUN_CACHE_DIR
if ($UseRunCache) {
    if (Test-Path $RunCacheDir) {
        Remove-Item -Recurse -Force -LiteralPath $RunCacheDir -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Force -Path $RunCacheDir | Out-Null
    $InitialManifest = [ordered]@{
        cache_run_id = [guid]::NewGuid().ToString()
        generated_at = $GeneratedAt
        provider = 'akshare'
        function_name = 'fund_etf_spot_em'
        cache_key = 'akshare.fund_etf_spot_em'
        ttl_seconds = 0
        row_count = 0
        source_mode = 'uat_run_cache'
        hit_count = 0
        miss_count = 0
        bypass_count = 0
        expired_count = 0
        cache_error_count = 0
        cache_file = (Join-Path $RunCacheDir 'akshare_fund_etf_spot_em.csv')
        notes = 'initialized by run_uat.ps1'
    }
    $InitialManifest | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $RunCacheDir 'cache_manifest.json') -Encoding UTF8
    $env:MARKET_GUARD_USE_UAT_RUN_CACHE = '1'
    $env:MARKET_GUARD_UAT_RUN_CACHE_DIR = $RunCacheDir
} else {
    Remove-Item Env:\MARKET_GUARD_USE_UAT_RUN_CACHE -ErrorAction SilentlyContinue
    Remove-Item Env:\MARKET_GUARD_UAT_RUN_CACHE_DIR -ErrorAction SilentlyContinue
}
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
    if ($Item.Name -notin $ModeItems[$Mode]) {
        $Results += [PSCustomObject]@{
            Name = $Item.Name
            Script = $Item.Script
            ExitCode = ''
            Status = 'skipped_by_profile'
            OutputDir = $Item.OutputDir
            IndexExists = $false
            UploadBundleExists = $false
            DebugBundleExists = $false
            CompletenessExists = $false
            HealthExists = $false
            RuntimeExists = $false
            ReconciliationExists = $false
            UnsupportedSymbolsExists = $false
            UnsupportedCount = 0
            UniverseType = ''
            PriceBlockExists = $false
            QuotePurpose = ''
            MissingFiles = @()
            AdviceHits = @()
            ElapsedSeconds = ''
            Mode = $Mode
            SkipReason = ('skipped in ' + $Mode + ' mode')
        }
        continue
    }

    if (-not (Test-Path $ScriptPath)) {
        $Results += [PSCustomObject]@{
            Name = $Item.Name
            Script = $Item.Script
            ExitCode = 1
            Status = 'failed'
            OutputDir = $Item.OutputDir
            IndexExists = $false
            UploadBundleExists = $false
            DebugBundleExists = $false
            CompletenessExists = $false
            HealthExists = $false
            RuntimeExists = $false
            ReconciliationExists = $false
            UnsupportedSymbolsExists = $false
            UnsupportedCount = 0
            UniverseType = ''
            PriceBlockExists = $false
            QuotePurpose = ''
            MissingFiles = @('script_missing:' + $Item.Script)
            AdviceHits = @()
            ElapsedSeconds = 0
            Mode = $Mode
            SkipReason = ''
        }
        $AnyFailed = $true
        continue
    }

    $Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    & $ScriptPath
    $ExitCode = $LASTEXITCODE
    $Stopwatch.Stop()
    $ElapsedSeconds = [Math]::Round($Stopwatch.Elapsed.TotalSeconds, 3)
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
    $LayerManifestExists = $false
    $LayerName = ''
    $LayerConfigSourcePath = ''
    $LayerConfiguredCount = ''
    $LayerLoadedCount = ''
    $LayerConfigMismatch = ''
    $LayerMissing = @()
    $LayerExtra = @()
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
    $LayerManifestPath = Join-Path $OutputPath 'layer_manifest.json'
    if (Test-Path $LayerManifestPath) {
        try {
            $LayerManifest = Get-Content $LayerManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $LayerManifestExists = $true
            $LayerName = [string]$LayerManifest.layer_name
            $LayerConfigSourcePath = [string]$LayerManifest.config_source_path
            $LayerConfiguredCount = [string]$LayerManifest.configured_symbol_count
            $LayerLoadedCount = [string]$LayerManifest.loaded_symbol_count
            $LayerConfigMismatch = ([string]$LayerManifest.config_mismatch).ToLowerInvariant()
            $LayerMissing = @($LayerManifest.missing_from_loaded)
            $LayerExtra = @($LayerManifest.extra_loaded_symbols)
        } catch {
            $LayerManifestExists = $false
            $LayerConfigMismatch = 'parse_error'
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
    if ($Item.Name -in @('tech_watchlist', 'tech_scan_ai', 'tech_operation_candidates')) {
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
        ElapsedSeconds = $ElapsedSeconds
        Mode = $Mode
        SkipReason = ''
        LayerManifestExists = $LayerManifestExists
        LayerName = $LayerName
        LayerConfigSourcePath = $LayerConfigSourcePath
        LayerConfiguredCount = $LayerConfiguredCount
        LayerLoadedCount = $LayerLoadedCount
        LayerConfigMismatch = $LayerConfigMismatch
        LayerMissing = $LayerMissing
        LayerExtra = $LayerExtra
    }
}
Pop-Location

$Passed = @($Results | Where-Object { $_.Status -eq 'passed' }).Count
$StrictBlocked = @($Results | Where-Object { $_.Status -eq 'strict_blocked_but_reported' }).Count
$Failed = @($Results | Where-Object { $_.Status -eq 'failed' }).Count
$SkippedByProfile = @($Results | Where-Object { $_.Status -eq 'skipped_by_profile' }).Count
$RunCount = @($Results | Where-Object { $_.Status -ne 'skipped_by_profile' }).Count
$AnyFailed = $Failed -gt 0
$CacheManifestPath = Join-Path $RunCacheDir 'cache_manifest.json'
$CacheManifest = $null
if ($UseRunCache -and (Test-Path $CacheManifestPath)) {
    try {
        $CacheManifest = Get-Content $CacheManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $CacheManifest = $null
    }
}
$RunCacheHitCount = if ($CacheManifest) { [int]$CacheManifest.hit_count } else { 0 }
$RunCacheMissCount = if ($CacheManifest) { [int]$CacheManifest.miss_count } else { 0 }
$RunCacheBypassCount = if ($CacheManifest) { [int]$CacheManifest.bypass_count } else { 0 }
$RunCacheErrorCount = if ($CacheManifest) { [int]$CacheManifest.cache_error_count } else { 0 }
$EstimatedSavedCalls = $RunCacheHitCount
$EstimatedSavedSeconds = if ($RunCacheHitCount -gt 0) { 'provider-dependent' } else { 0 }

$Lines = @()
$Lines += '# market_price_guard UAT Summary'
$Lines += ''
$Lines += ('- generated_at: ' + $GeneratedAt)
$Lines += ('- mode: ' + $Mode)
$Lines += ('- profile_explanation: ' + $ModeExplanation[$Mode])
$Lines += ('- use_run_cache: ' + $UseRunCache.IsPresent.ToString().ToLowerInvariant())
$Lines += ('- run_cache_dir: ' + ($(if ($UseRunCache) { $RunCacheDir } else { '' })))
$Lines += '- cache_scope: uat_run'
$Lines += '- cache_enabled_functions: akshare.fund_etf_spot_em'
$Lines += ('- run_cache_hit_count: ' + $RunCacheHitCount)
$Lines += ('- run_cache_miss_count: ' + $RunCacheMissCount)
$Lines += ('- run_cache_bypass_count: ' + $RunCacheBypassCount)
$Lines += ('- run_cache_error_count: ' + $RunCacheErrorCount)
$Lines += ('- estimated_cache_saved_calls: ' + $EstimatedSavedCalls)
$Lines += ('- estimated_cache_saved_seconds: ' + $EstimatedSavedSeconds)
$Lines += ('- total_defined: ' + $Results.Count)
$Lines += ('- run_count: ' + $RunCount)
$Lines += ('- passed: ' + $Passed)
$Lines += ('- strict_blocked_but_reported: ' + $StrictBlocked)
$Lines += ('- failed: ' + $Failed)
$Lines += ('- skipped_by_profile: ' + $SkippedByProfile)
$Lines += ('- total: ' + $Results.Count)
$Lines += ''
$Lines += 'strict=2 means the price guard blocked operation; it is not a UAT failure when reports are generated and blocking is explained.'
$Lines += 'skipped_by_profile means the item is intentionally skipped by the selected UAT mode and is not a failure.'
$Lines += ''
$Lines += '## Slowest Items'
$Lines += ''
$Lines += '| item | elapsed_seconds | status |'
$Lines += '|---|---:|---|'
$Slowest = $Results | Where-Object { $_.Status -ne 'skipped_by_profile' } | Sort-Object {[double]$_.ElapsedSeconds} -Descending | Select-Object -First 5
foreach ($Slow in $Slowest) {
    $Lines += ('| ' + $Slow.Name + ' | ' + $Slow.ElapsedSeconds + ' | ' + $Slow.Status + ' |')
}
if (($Slowest | Measure-Object).Count -eq 0) {
    $Lines += '| none | 0 | skipped |'
}
$Lines += ''
$Lines += '## Items'

foreach ($Result in $Results) {
    $Lines += ''
    $Lines += ('### ' + $Result.Name)
    $Lines += ('- command/script: ' + $Result.Script)
    $Lines += ('- exit_code: ' + $Result.ExitCode)
    $Lines += ('- status: ' + $Result.Status)
    $Lines += ('- mode: ' + $Result.Mode)
    $Lines += ('- elapsed_seconds: ' + $Result.ElapsedSeconds)
    $Lines += ('- item_cache_status: ' + ($(if ($UseRunCache -and $Result.Status -ne 'skipped_by_profile') { 'not_collected' } else { '' })))
    $Lines += ('- item_cache_note: ' + ($(if ($UseRunCache -and $Result.Status -ne 'skipped_by_profile') { 'see run-level cache summary' } else { '' })))
    if ($Result.Status -eq 'skipped_by_profile') {
        $Lines += ('- skip_reason: ' + $Result.SkipReason)
    }
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
    $Lines += ('- layer_manifest.json exists: ' + $Result.LayerManifestExists)
    $Lines += ('- layer_name: ' + $Result.LayerName)
    $Lines += ('- config_source_path: ' + $Result.LayerConfigSourcePath)
    $Lines += ('- configured_symbol_count: ' + $Result.LayerConfiguredCount)
    $Lines += ('- loaded_symbol_count: ' + $Result.LayerLoadedCount)
    $Lines += ('- config_mismatch: ' + $Result.LayerConfigMismatch)
    $Lines += ('- missing_from_loaded: ' + ($(if ($Result.LayerMissing.Count -gt 0) { $Result.LayerMissing -join ', ' } else { 'none' })))
    $Lines += ('- extra_loaded_symbols: ' + ($(if ($Result.LayerExtra.Count -gt 0) { $Result.LayerExtra -join ', ' } else { 'none' })))
    if ($Result.Name -in @('tech_watchlist', 'tech_scan_ai', 'tech_operation_candidates')) {
        $Lines += '- strict_pollution_isolation: candidate/scan/operation-candidate universes are non-strict reference outputs.'
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

if ($null -ne $PreviousUseRunCache) {
    $env:MARKET_GUARD_USE_UAT_RUN_CACHE = $PreviousUseRunCache
} else {
    Remove-Item Env:\MARKET_GUARD_USE_UAT_RUN_CACHE -ErrorAction SilentlyContinue
}
if ($null -ne $PreviousRunCacheDir) {
    $env:MARKET_GUARD_UAT_RUN_CACHE_DIR = $PreviousRunCacheDir
} else {
    Remove-Item Env:\MARKET_GUARD_UAT_RUN_CACHE_DIR -ErrorAction SilentlyContinue
}

Write-Host ('UAT summary: ' + $SummaryPath)
if ($AnyFailed) {
    exit 1
}
exit 0
