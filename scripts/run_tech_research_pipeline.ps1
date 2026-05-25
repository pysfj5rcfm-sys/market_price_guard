param(
    [switch]$UseRunCache,
    [switch]$StopOnFailure,
    [switch]$SkipScan,
    [switch]$SkipWatchlist,
    [switch]$SkipOperationCandidates,
    [switch]$SkipTechFast,
    [switch]$SkipMinuteProbe,
    [switch]$SkipIntradayMetrics,
    [string]$ScanMode = 'fast',
    [string]$MinuteMode = 'balanced',
    [int]$MinuteWorkers = 3
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

if ($ScanMode -notin @('fast', 'diagnostic')) {
    Write-Host 'Invalid ScanMode. Valid values: fast, diagnostic.'
    exit 1
}
if ($MinuteMode -notin @('fast', 'balanced', 'diagnostic')) {
    Write-Host 'Invalid MinuteMode. Valid values: fast, balanced, diagnostic.'
    exit 1
}
if ($MinuteWorkers -lt 1) {
    Write-Host 'Invalid MinuteWorkers. Use an integer >= 1.'
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$OutputDir = Join-Path $ProjectRoot 'outputs_tech_pipeline_latest'
$CacheDir = Join-Path $ProjectRoot 'outputs_tech_pipeline_cache_latest'
$SummaryPath = Join-Path $OutputDir 'pipeline_summary.md'
$ManifestPath = Join-Path $OutputDir 'pipeline_manifest.json'
$LayerManifestPath = Join-Path $OutputDir 'pipeline_layer_manifest.json'
$UploadManifestPath = Join-Path $OutputDir 'upload_manifest.md'

$PreviousUseRunCache = $env:MARKET_GUARD_USE_UAT_RUN_CACHE
$PreviousRunCacheDir = $env:MARKET_GUARD_UAT_RUN_CACHE_DIR

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$PipelineStartedAt = (Get-Date).ToUniversalTime()
$GeneratedAt = $PipelineStartedAt.ToString('o')

if ($UseRunCache) {
    if (Test-Path $CacheDir) {
        Remove-Item -Recurse -Force -LiteralPath $CacheDir -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
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
        cache_file = (Join-Path $CacheDir 'akshare_fund_etf_spot_em.csv')
        notes = 'initialized by run_tech_research_pipeline.ps1'
    }
    $InitialManifest | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $CacheDir 'cache_manifest.json') -Encoding UTF8
    $env:MARKET_GUARD_USE_UAT_RUN_CACHE = '1'
    $env:MARKET_GUARD_UAT_RUN_CACHE_DIR = $CacheDir
} else {
    Remove-Item Env:\MARKET_GUARD_USE_UAT_RUN_CACHE -ErrorAction SilentlyContinue
    Remove-Item Env:\MARKET_GUARD_UAT_RUN_CACHE_DIR -ErrorAction SilentlyContinue
}

$Steps = @(
    @{ Name = 'tech_scan_ai'; Script = 'run_tech_scan_ai.ps1'; Args = [string[]]@('-Mode', $ScanMode); OutputDir = 'outputs_tech_scan_ai_latest'; Skip = $SkipScan.IsPresent },
    @{ Name = 'tech_watchlist'; Script = 'run_tech_watchlist.ps1'; OutputDir = 'outputs_tech_watchlist_latest'; Skip = $SkipWatchlist.IsPresent },
    @{ Name = 'tech_operation_candidates'; Script = 'run_tech_operation_candidates.ps1'; OutputDir = 'outputs_tech_operation_candidates_latest'; Skip = $SkipOperationCandidates.IsPresent },
    @{ Name = 'tech_fast_strict'; Script = 'run_tech_fast_strict.ps1'; OutputDir = 'outputs_tech_latest'; Skip = $SkipTechFast.IsPresent },
    @{ Name = 'tech_minute_probe'; Script = 'run_tech_minute_probe.ps1'; Args = [string[]]@('-Mode', $MinuteMode, '-MinuteWorkers', [string]$MinuteWorkers); OutputDir = 'outputs_tech_minute_probe_latest'; Skip = $SkipMinuteProbe.IsPresent },
    @{ Name = 'tech_intraday_metrics'; Script = 'run_tech_intraday_metrics.ps1'; OutputDir = 'outputs_tech_intraday_latest'; Skip = $SkipIntradayMetrics.IsPresent }
)

$Results = @()
$Stopped = $false

Push-Location $ProjectRoot
foreach ($Step in $Steps) {
    $ScriptPath = Join-Path $ScriptDir $Step['Script']
    if ($Stopped -or $Step['Skip']) {
        $SkipReason = if ($Stopped) { 'stopped after previous failed step' } else { 'skipped by parameter' }
        $Results += [PSCustomObject]@{
            name = $Step['Name']
            command = $Step['Script']
            output_dir = $Step['OutputDir']
            started_at = ''
            finished_at = ''
            elapsed_seconds = ''
            exit_code = ''
            status = 'skipped_by_parameter'
            skipped = $true
            skip_reason = $SkipReason
            runtime_warning = $false
            max_run_seconds = ''
        }
        continue
    }

    $StartedAt = (Get-Date).ToUniversalTime()
    $Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    if (-not (Test-Path $ScriptPath)) {
        $ExitCode = 1
    } else {
        $StepArgs = @()
        if ($Step['Name'] -eq 'tech_scan_ai') {
            $StepArgs = @('-Mode', $ScanMode)
            & $ScriptPath -Mode $ScanMode
        } elseif ($Step['Name'] -eq 'tech_minute_probe') {
            $StepArgs = @('-Mode', $MinuteMode, '-MinuteWorkers', [string]$MinuteWorkers)
            & $ScriptPath -Mode $MinuteMode -MinuteWorkers $MinuteWorkers
        } else {
            & $ScriptPath
        }
        $ExitCode = $LASTEXITCODE
    }
    $Stopwatch.Stop()
    $FinishedAt = (Get-Date).ToUniversalTime()
    $ElapsedSeconds = [Math]::Round($Stopwatch.Elapsed.TotalSeconds, 3)
    $OutputPath = Join-Path $ProjectRoot $Step['OutputDir']
    $StrictReportsExist = (Test-Path (Join-Path $OutputPath '0_upload_bundle.md')) -and (Test-Path (Join-Path $OutputPath 'debug_bundle.md')) -and (Test-Path (Join-Path $OutputPath 'data_completeness_report.md'))
    $Status = 'passed'
    if ($ExitCode -eq 2 -and $StrictReportsExist) {
        $Status = 'strict_blocked_but_reported'
    } elseif ($ExitCode -ne 0) {
        $Status = 'failed'
    }
    $RuntimePath = Join-Path $OutputPath 'runtime_diagnostics.md'
    $RuntimeWarning = $false
    $MaxRunSeconds = ''
    if (Test-Path $RuntimePath) {
        $RuntimeContent = Get-Content $RuntimePath -Raw -Encoding UTF8
        if ($RuntimeContent -match 'run_time_budget_exceeded:\s*(True|true)') {
            $RuntimeWarning = $true
        }
        if ($RuntimeContent -match 'max_run_seconds:\s*([0-9.]+)') {
            $MaxRunSeconds = $Matches[1]
        }
    }
    $Results += [PSCustomObject]@{
        name = $Step['Name']
        command = ($Step['Script'] + ' ' + (($StepArgs | ForEach-Object { [string]$_ }) -join ' ')).Trim()
        output_dir = $Step['OutputDir']
        started_at = $StartedAt.ToString('o')
        finished_at = $FinishedAt.ToString('o')
        elapsed_seconds = $ElapsedSeconds
        exit_code = $ExitCode
        status = $Status
        skipped = $false
        skip_reason = ''
        runtime_warning = $RuntimeWarning
        max_run_seconds = $MaxRunSeconds
    }
    if ($Status -eq 'failed' -and $StopOnFailure) {
        $Stopped = $true
    }
}
Pop-Location

$PipelineFinishedAt = (Get-Date).ToUniversalTime()
$TotalElapsedSeconds = [Math]::Round(($PipelineFinishedAt - $PipelineStartedAt).TotalSeconds, 3)

$CacheManifestPath = Join-Path $CacheDir 'cache_manifest.json'
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

$Passed = @($Results | Where-Object { $_.status -eq 'passed' }).Count
$Failed = @($Results | Where-Object { $_.status -eq 'failed' }).Count
$StrictBlocked = @($Results | Where-Object { $_.status -eq 'strict_blocked_but_reported' }).Count
$Skipped = @($Results | Where-Object { $_.status -eq 'skipped_by_parameter' }).Count
$RunSteps = @($Results | Where-Object { $_.status -ne 'skipped_by_parameter' }).Count

$LayerManifests = @()
foreach ($Step in $Steps) {
    $StepOutputPath = Join-Path $ProjectRoot $Step['OutputDir']
    $StepLayerManifestPath = Join-Path $StepOutputPath 'layer_manifest.json'
    if (Test-Path $StepLayerManifestPath) {
        try {
            $LayerData = Get-Content $StepLayerManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $LayerManifests += $LayerData
        } catch {
            $LayerManifests += [PSCustomObject]@{
                layer_name = $Step['Name']
                config_source_path = ('manifest_parse_error:' + $StepLayerManifestPath)
                configured_symbol_count = 0
                loaded_symbol_count = 0
                config_mismatch = $true
                missing_from_loaded = @()
                extra_loaded_symbols = @()
            }
        }
    } else {
        $LayerManifests += [PSCustomObject]@{
            layer_name = $Step['Name']
            config_source_path = ('manifest_missing:' + $Step['OutputDir'] + '/layer_manifest.json')
            configured_symbol_count = 0
            loaded_symbol_count = 0
            config_mismatch = $true
            missing_from_loaded = @()
            extra_loaded_symbols = @()
        }
    }
}
$LayerMismatchCount = @($LayerManifests | Where-Object { $_.config_mismatch }).Count

$Lines = @()
$Lines += '# Tech Research Pipeline Summary'
$Lines += ''
$Lines += ('- generated_at: ' + $GeneratedAt)
$Lines += '- pipeline_name: tech_research_pipeline'
$Lines += ('- use_run_cache: ' + $UseRunCache.IsPresent.ToString().ToLowerInvariant())
$Lines += ('- scan_mode: ' + $ScanMode)
$Lines += ('- minute_mode: ' + $MinuteMode)
$Lines += ('- minute_workers: ' + $MinuteWorkers)
$Lines += ('- cache_dir: ' + ($(if ($UseRunCache) { $CacheDir } else { '' })))
$Lines += ('- total_steps: ' + $Results.Count)
$Lines += ('- run_steps: ' + $RunSteps)
$Lines += ('- skipped_steps: ' + $Skipped)
$Lines += ('- passed: ' + $Passed)
$Lines += ('- strict_blocked_but_reported: ' + $StrictBlocked)
$Lines += ('- failed: ' + $Failed)
$Lines += ('- total_elapsed_seconds: ' + $TotalElapsedSeconds)
$Lines += ''
$Lines += '## Steps'
$Lines += ''
$Lines += '| step | status | exit_code | elapsed_seconds | output_dir |'
$Lines += '|---|---|---:|---:|---|'
foreach ($Result in $Results) {
    $Lines += ('| ' + $Result.name + ' | ' + $Result.status + ' | ' + $Result.exit_code + ' | ' + $Result.elapsed_seconds + ' | ' + $Result.output_dir + ' |')
}
$Lines += ''
$Lines += '## Cache Summary'
$Lines += ''
$Lines += '- cache_enabled_functions: akshare.fund_etf_spot_em'
$Lines += ('- run_cache_hit_count: ' + $RunCacheHitCount)
$Lines += ('- run_cache_miss_count: ' + $RunCacheMissCount)
$Lines += ('- run_cache_bypass_count: ' + $RunCacheBypassCount)
$Lines += ('- run_cache_error_count: ' + $RunCacheErrorCount)
$Lines += '- item_cache_status: not_collected'
$Lines += '- item_cache_note: see run-level cache summary'
$Lines += ''
$Lines += '## Layer Config Summary'
$Lines += ''
if ($LayerMismatchCount -gt 0) {
    $Lines += 'CONFIG_MISMATCH: true'
    $Lines += ''
}
$Lines += '| layer | config_source_path | configured | loaded | mismatch | missing | extra |'
$Lines += '|---|---|---:|---:|---|---|---|'
foreach ($Layer in $LayerManifests) {
    $Missing = if ($Layer.missing_from_loaded) { ($Layer.missing_from_loaded -join ', ') } else { 'none' }
    $Extra = if ($Layer.extra_loaded_symbols) { ($Layer.extra_loaded_symbols -join ', ') } else { 'none' }
    $Lines += ('| ' + $Layer.layer_name + ' | ' + $Layer.config_source_path + ' | ' + $Layer.configured_symbol_count + ' | ' + $Layer.loaded_symbol_count + ' | ' + ([string]$Layer.config_mismatch).ToLowerInvariant() + ' | ' + $Missing + ' | ' + $Extra + ' |')
}
$Lines += ''
$Lines += '## Output Dirs Generated'
foreach ($Step in $Steps) {
    $Lines += ('- ' + $Step['OutputDir'])
}
$Lines += ''
$Lines += '## Slow Steps / Runtime Warnings'
$Warnings = @($Results | Where-Object { $_.runtime_warning })
if ($Warnings.Count -eq 0) {
    $Lines += '- none'
} else {
    $Lines += '| step_name | elapsed_seconds | max_run_seconds | warning |'
    $Lines += '|---|---:|---:|---|'
    foreach ($Warning in $Warnings) {
        $Note = if ($Warning.name -eq 'tech_scan_ai') { 'scan_ai runtime exceeded budget; provider timeout/runtime polish remains backlog.' } elseif ($Warning.name -eq 'tech_minute_probe') { 'minute_probe runtime exceeded budget; provider or symbol-level minute requests remain slow.' } else { 'run_time_budget_exceeded' }
        $Lines += ('| ' + $Warning.name + ' | ' + $Warning.elapsed_seconds + ' | ' + $Warning.max_run_seconds + ' | ' + $Note + ' |')
    }
}
$Lines += ''
$Lines += '## Safety Note'
$Lines += 'This pipeline generates data outputs only. It does not modify config, does not promote symbols, and does not generate trading advice.'
$Lines += 'Data-only pipeline: no config changes, no automatic symbol promotion, no trading advice.'
$Lines | Set-Content $SummaryPath -Encoding UTF8

$Manifest = New-Object PSObject -Property ([ordered]@{
    pipeline_name = 'tech_research_pipeline';
    generated_at = $GeneratedAt;
    use_run_cache = $UseRunCache.IsPresent;
    scan_mode = $ScanMode;
    minute_mode = $MinuteMode;
    minute_workers = $MinuteWorkers;
    cache_dir = $(if ($UseRunCache) { $CacheDir } else { '' });
    steps = @($Results);
    layer_config_summary = @($LayerManifests);
    summary = New-Object PSObject -Property ([ordered]@{
        passed = $Passed;
        failed = $Failed;
        strict_blocked_but_reported = $StrictBlocked;
        skipped_by_parameter = $Skipped;
        run_cache_hit_count = $RunCacheHitCount;
        run_cache_miss_count = $RunCacheMissCount;
        run_cache_bypass_count = $RunCacheBypassCount;
        run_cache_error_count = $RunCacheErrorCount;
        total_elapsed_seconds = $TotalElapsedSeconds;
    })
})
$Manifest | ConvertTo-Json -Depth 6 | Set-Content $ManifestPath -Encoding UTF8

$PipelineLayerManifest = New-Object PSObject -Property ([ordered]@{
    pipeline_name = 'tech_research_pipeline';
    generated_at = $GeneratedAt;
    layer_mismatch_count = $LayerMismatchCount;
    layers = @($LayerManifests);
})
$PipelineLayerManifest | ConvertTo-Json -Depth 8 | Set-Content $LayerManifestPath -Encoding UTF8

$UploadLines = @(
    '# Tech Research Pipeline Upload Manifest',
    '',
    '## Core Trading State',
    '- outputs_tech_latest/0_upload_bundle.md',
    '',
    '## Full Research Chain',
    '- outputs_tech_pipeline_latest/pipeline_summary.md',
    '- outputs_tech_scan_ai_latest/0_upload_bundle.md',
    '- outputs_tech_scan_ai_latest/scan_universe_report.md',
    '- outputs_tech_watchlist_latest/0_upload_bundle.md',
    '- outputs_tech_watchlist_latest/candidate_watchlist_report.md',
    '- outputs_tech_operation_candidates_latest/0_upload_bundle.md',
    '- outputs_tech_operation_candidates_latest/operation_candidate_report.md',
    '- outputs_tech_latest/0_upload_bundle.md',
    '- outputs_tech_minute_probe_latest/0_upload_bundle.md',
    '- outputs_tech_intraday_latest/0_upload_bundle.md',
    '- outputs_tech_intraday_latest/reference_vwap_report.md',
    '',
    '## Compact Upload',
    '- outputs_tech_pipeline_latest/pipeline_summary.md',
    '- outputs_tech_latest/0_upload_bundle.md',
    '- outputs_tech_operation_candidates_latest/0_upload_bundle.md',
    '- outputs_tech_intraday_latest/0_upload_bundle.md',
    '',
    '## VWAP / Intraday Position',
    '- outputs_tech_intraday_latest/0_upload_bundle.md',
    '- outputs_tech_intraday_latest/reference_vwap_report.md',
    '',
    '## Runtime Debug',
    '- outputs_tech_pipeline_latest/pipeline_summary.md',
    '- corresponding step runtime_diagnostics.md',
    '',
    '## Notes',
    '- GOLD_CNY is manual price only and does not support reference VWAP / intraday metrics.',
    '- This manifest is for data review only and does not provide trading advice.'
)
$UploadLines | Set-Content $UploadManifestPath -Encoding UTF8

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

Write-Host ('Pipeline summary: ' + $SummaryPath)
if ($Failed -gt 0) {
    exit 1
}
exit 0
