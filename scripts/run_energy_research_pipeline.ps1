param(
    [switch]$StopOnFailure,
    [switch]$SkipScan,
    [switch]$SkipWatchlist,
    [switch]$SkipOperationCandidates,
    [switch]$SkipEnergyFast,
    [string]$ScanMode = 'fast'
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

if ($ScanMode -notin @('fast', 'diagnostic')) {
    Write-Host 'Invalid ScanMode. Valid values: fast, diagnostic.'
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$OutputDir = Join-Path $ProjectRoot 'outputs_energy_pipeline_latest'
$QuoteCacheDir = Join-Path $ProjectRoot 'outputs_energy_pipeline_quote_cache_latest'
$SummaryPath = Join-Path $OutputDir 'pipeline_summary.md'
$ManifestPath = Join-Path $OutputDir 'pipeline_manifest.json'
$LayerManifestPath = Join-Path $OutputDir 'pipeline_layer_manifest.json'
$UploadManifestPath = Join-Path $OutputDir 'upload_manifest.md'

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
if (Test-Path $QuoteCacheDir) {
    Remove-Item -Recurse -Force -LiteralPath $QuoteCacheDir -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $QuoteCacheDir | Out-Null
$PipelineStartedAt = (Get-Date).ToUniversalTime()
$GeneratedAt = $PipelineStartedAt.ToString('o')
$PreviousUseQuoteCache = $env:MARKET_GUARD_USE_QUOTE_RUN_CACHE
$PreviousQuoteCacheDir = $env:MARKET_GUARD_QUOTE_RUN_CACHE_DIR
$env:MARKET_GUARD_USE_QUOTE_RUN_CACHE = '1'
$env:MARKET_GUARD_QUOTE_RUN_CACHE_DIR = $QuoteCacheDir

$Steps = @(
    @{ Name = 'energy_scan'; Script = 'run_energy_scan.ps1'; Args = [string[]]@('-Mode', $ScanMode); OutputDir = 'outputs_energy_scan_latest'; Skip = $SkipScan.IsPresent },
    @{ Name = 'energy_watchlist'; Script = 'run_energy_watchlist.ps1'; OutputDir = 'outputs_energy_watchlist_latest'; Skip = $SkipWatchlist.IsPresent },
    @{ Name = 'energy_operation_candidates'; Script = 'run_energy_operation_candidates.ps1'; OutputDir = 'outputs_energy_operation_candidates_latest'; Skip = $SkipOperationCandidates.IsPresent },
    @{ Name = 'energy_fast_strict'; Script = 'run_energy_fast_strict.ps1'; OutputDir = 'outputs_energy_latest'; Skip = $SkipEnergyFast.IsPresent }
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
    $StepArgs = @()
    if (-not (Test-Path $ScriptPath)) {
        $ExitCode = 1
    } elseif ($Step['Name'] -eq 'energy_scan') {
        $StepArgs = @('-Mode', $ScanMode)
        & $ScriptPath -Mode $ScanMode
        $ExitCode = $LASTEXITCODE
    } else {
        & $ScriptPath
        $ExitCode = $LASTEXITCODE
    }
    $Stopwatch.Stop()
    $FinishedAt = (Get-Date).ToUniversalTime()
    $ElapsedSeconds = [Math]::Round($Stopwatch.Elapsed.TotalSeconds, 3)
    $StepOutputPath = Join-Path $ProjectRoot $Step['OutputDir']
    $ReportsExist = (Test-Path (Join-Path $StepOutputPath '0_upload_bundle.md')) -and (Test-Path (Join-Path $StepOutputPath 'debug_bundle.md')) -and (Test-Path (Join-Path $StepOutputPath 'data_completeness_report.md'))
    $Status = 'passed'
    if ($ExitCode -eq 2 -and $ReportsExist) {
        $Status = 'strict_blocked_but_reported'
    } elseif ($ExitCode -ne 0) {
        $Status = 'failed'
    }
    $RuntimePath = Join-Path $StepOutputPath 'runtime_diagnostics.md'
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
$Passed = @($Results | Where-Object { $_.status -eq 'passed' }).Count
$Failed = @($Results | Where-Object { $_.status -eq 'failed' }).Count
$StrictBlocked = @($Results | Where-Object { $_.status -eq 'strict_blocked_but_reported' }).Count
$Skipped = @($Results | Where-Object { $_.status -eq 'skipped_by_parameter' }).Count

$LayerManifests = @()
$CompletenessRows = @()
foreach ($Step in $Steps) {
    $StepOutputPath = Join-Path $ProjectRoot $Step['OutputDir']
    $StepLayerManifestPath = Join-Path $StepOutputPath 'layer_manifest.json'
    if (Test-Path $StepLayerManifestPath) {
        try {
            $LayerManifests += Get-Content $StepLayerManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        } catch {
            $LayerManifests += [PSCustomObject]@{
                account = 'energy'
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
            account = 'energy'
            layer_name = $Step['Name']
            config_source_path = ('manifest_missing:' + $Step['OutputDir'] + '/layer_manifest.json')
            configured_symbol_count = 0
            loaded_symbol_count = 0
            config_mismatch = $true
            missing_from_loaded = @()
            extra_loaded_symbols = @()
        }
    }
    $CsvPath = Join-Path $StepOutputPath 'prices_snapshot.csv'
    $Rows = @()
    if (Test-Path $CsvPath) {
        $Rows = @(Import-Csv $CsvPath)
    }
    $CompletenessRows += [PSCustomObject]@{
        layer = $Step['Name']
        total_symbols = $Rows.Count
        successful_quote_count = @($Rows | Where-Object { $_.price -ne '' }).Count
        failed_quote_count = @($Rows | Where-Object { $_.price -eq '' }).Count
        provider_missing_count = @($Rows | Where-Object { $_.selected_provider -eq '' }).Count
        unsupported_count = @($Rows | Where-Object { $_.unsupported_reason -ne '' }).Count
        stale_count = @($Rows | Where-Object { ([string]$_.is_stale).ToLowerInvariant() -eq 'true' }).Count
        usable_for_reference_count = @($Rows | Where-Object { ([string]$_.usable_for_reference).ToLowerInvariant() -eq 'true' }).Count
        usable_for_operation_count = @($Rows | Where-Object { ([string]$_.usable_for_operation).ToLowerInvariant() -eq 'true' }).Count
    }
}
$LayerMismatchCount = @($LayerManifests | Where-Object { $_.config_mismatch }).Count
$QuoteCacheManifestPath = Join-Path $QuoteCacheDir 'quote_cache_manifest.json'
$QuoteCacheManifest = $null
if (Test-Path $QuoteCacheManifestPath) {
    try {
        $QuoteCacheManifest = Get-Content $QuoteCacheManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $QuoteCacheManifest = $null
    }
}
$QuoteCacheHitCount = if ($QuoteCacheManifest) { [int]$QuoteCacheManifest.quote_cache_hit_count } else { 0 }
$QuoteCacheMissCount = if ($QuoteCacheManifest) { [int]$QuoteCacheManifest.quote_cache_miss_count } else { 0 }
$QuoteCacheFailureHitCount = if ($QuoteCacheManifest) { [int]$QuoteCacheManifest.quote_cache_failure_hit_count } else { 0 }
$QuoteCacheSuccessHitCount = if ($QuoteCacheManifest) { [int]$QuoteCacheManifest.quote_cache_success_hit_count } else { 0 }
$RepeatedProviderPreventedCount = if ($QuoteCacheManifest) { [int]$QuoteCacheManifest.repeated_provider_call_prevented_count } else { 0 }

$Lines = @()
$Lines += '# Energy Research Pipeline Summary'
$Lines += ''
$Lines += ('- generated_at: ' + $GeneratedAt)
$Lines += '- account: energy'
$Lines += '- pipeline_name: energy_research_pipeline'
$Lines += '- version: v0.7.5'
$Lines += ('- scan_mode: ' + $ScanMode)
$Lines += ('- total_steps: ' + $Results.Count)
$Lines += ('- passed: ' + $Passed)
$Lines += ('- strict_blocked_but_reported: ' + $StrictBlocked)
$Lines += ('- failed: ' + $Failed)
$Lines += ('- skipped_steps: ' + $Skipped)
$Lines += ('- total_elapsed_seconds: ' + $TotalElapsedSeconds)
$Lines += '- no minute_probe'
$Lines += '- no intraday_metrics'
$Lines += '- no VWAP'
$Lines += '- no trading advice'
$Lines += ''
$Lines += '## Steps'
$Lines += ''
$Lines += '| step | status | exit_code | elapsed_seconds | output_dir |'
$Lines += '|---|---|---:|---:|---|'
foreach ($Result in $Results) {
    $Lines += ('| ' + $Result.name + ' | ' + $Result.status + ' | ' + $Result.exit_code + ' | ' + $Result.elapsed_seconds + ' | ' + $Result.output_dir + ' |')
}
$Lines += ''
$Lines += '## Layer Config Summary'
$Lines += ''
if ($LayerMismatchCount -gt 0) {
    $Lines += 'CONFIG_MISMATCH: true'
    $Lines += ''
}
$Lines += '| layer | configured | loaded | mismatch |'
$Lines += '|---|---:|---:|---|'
foreach ($Layer in $LayerManifests) {
    $Lines += ('| ' + $Layer.layer_name + ' | ' + $Layer.configured_symbol_count + ' | ' + $Layer.loaded_symbol_count + ' | ' + ([string]$Layer.config_mismatch).ToLowerInvariant() + ' |')
}
$Lines += ''
$Lines += '## Data Completeness Summary'
$Lines += ''
$Lines += '| layer | total | success | failed | provider_missing | unsupported | stale | usable_reference | usable_operation |'
$Lines += '|---|---:|---:|---:|---:|---:|---:|---:|---:|'
foreach ($Row in $CompletenessRows) {
    $Lines += ('| ' + $Row.layer + ' | ' + $Row.total_symbols + ' | ' + $Row.successful_quote_count + ' | ' + $Row.failed_quote_count + ' | ' + $Row.provider_missing_count + ' | ' + $Row.unsupported_count + ' | ' + $Row.stale_count + ' | ' + $Row.usable_for_reference_count + ' | ' + $Row.usable_for_operation_count + ' |')
}
$Lines += ''
$Lines += '## Cache / Reuse Summary'
$Lines += ''
$Lines += ('- quote_cache_hit_count: ' + $QuoteCacheHitCount)
$Lines += ('- quote_cache_miss_count: ' + $QuoteCacheMissCount)
$Lines += ('- quote_cache_failure_hit_count: ' + $QuoteCacheFailureHitCount)
$Lines += ('- quote_cache_success_hit_count: ' + $QuoteCacheSuccessHitCount)
$Lines += '- batch_cache_hit_count: see step runtime_diagnostics.md'
$Lines += '- batch_cache_miss_count: see step runtime_diagnostics.md'
$Lines += ('- repeated_provider_call_prevented_count: ' + $RepeatedProviderPreventedCount)
$Lines += '- repeated_batch_call_prevented_count: see step runtime_diagnostics.md'
$Lines += '- cache_hit_by_layer: see step runtime_diagnostics.md'
$Lines += '- cache_hit_by_provider: see step runtime_diagnostics.md'
$Lines += ''
$Lines += '## Runtime Diagnostics Summary'
$Lines += ''
$Lines += '| step | runtime_warning | max_run_seconds |'
$Lines += '|---|---|---:|'
foreach ($Result in $Results) {
    $Lines += ('| ' + $Result.name + ' | ' + ([string]$Result.runtime_warning).ToLowerInvariant() + ' | ' + $Result.max_run_seconds + ' |')
}
$Lines += ''
$Lines += '## Runtime Budget Summary'
$Lines += ''
$Lines += '| step | run_time_budget_exceeded | provider_timeout_count | skipped_by_runtime_budget | circuit_open_count |'
$Lines += '|---|---|---:|---:|---:|'
foreach ($Result in $Results) {
    $RuntimePath = Join-Path (Join-Path $ProjectRoot $Result.output_dir) 'runtime_diagnostics.md'
    $BudgetExceeded = 'unknown'
    $TimeoutCount = '0'
    $SkippedBudget = '0'
    $CircuitCount = '0'
    if (Test-Path $RuntimePath) {
        $RuntimeContent = Get-Content $RuntimePath -Raw -Encoding UTF8
        if ($RuntimeContent -match 'run_time_budget_exceeded:\s*([A-Za-z]+)') { $BudgetExceeded = $Matches[1].ToLowerInvariant() }
        if ($RuntimeContent -match 'provider_timeout_count:\s*(\d+)') { $TimeoutCount = $Matches[1] }
        if ($RuntimeContent -match 'provider_skipped_by_runtime_budget_count:\s*(\d+)') { $SkippedBudget = $Matches[1] }
        if ($RuntimeContent -match 'provider_circuit_open_count:\s*(\d+)') { $CircuitCount = $Matches[1] }
    }
    $Lines += ('| ' + $Result.name + ' | ' + $BudgetExceeded + ' | ' + $TimeoutCount + ' | ' + $SkippedBudget + ' | ' + $CircuitCount + ' |')
}
$Lines += ''
$Lines += '## Provider Health Summary'
$Lines += ''
$Lines += '| step | provider_health_report | planned_actual_summary |'
$Lines += '|---|---|---|'
foreach ($Result in $Results) {
    $HealthPath = Join-Path (Join-Path $ProjectRoot $Result.output_dir) 'provider_health_report.md'
    $HealthExists = Test-Path $HealthPath
    $SummaryState = if ($HealthExists) {
        $HealthContent = Get-Content $HealthPath -Raw -Encoding UTF8
        if ($HealthContent -match '## Provider Health Summary') { 'available' } else { 'legacy_format' }
    } else {
        'missing'
    }
    $Lines += ('| ' + $Result.name + ' | ' + ([string]$HealthExists).ToLowerInvariant() + ' | ' + $SummaryState + ' |')
}
$Lines += ''
$Lines += '## Safety Statements'
$Lines += ''
$Lines += '- operation_candidate is not an execution list.'
$Lines += '- watchlist is not an execution layer.'
$Lines += '- scan is not a trading signal.'
$Lines += '- no trading advice is generated.'
$Lines += '- scan, watchlist, and operation_candidate results are not promoted automatically.'
$Lines | Set-Content $SummaryPath -Encoding UTF8

$Manifest = New-Object PSObject -Property ([ordered]@{
    account = 'energy';
    pipeline_name = 'energy_research_pipeline';
    version = 'v0.7.5';
    generated_at = $GeneratedAt;
    scan_mode = $ScanMode;
    steps = @($Results);
    layer_config_summary = @($LayerManifests);
    data_completeness_summary = @($CompletenessRows);
    summary = New-Object PSObject -Property ([ordered]@{
        passed = $Passed;
        failed = $Failed;
        strict_blocked_but_reported = $StrictBlocked;
        skipped_by_parameter = $Skipped;
        total_elapsed_seconds = $TotalElapsedSeconds;
        quote_cache_hit_count = $QuoteCacheHitCount;
        quote_cache_miss_count = $QuoteCacheMissCount;
        quote_cache_failure_hit_count = $QuoteCacheFailureHitCount;
        quote_cache_success_hit_count = $QuoteCacheSuccessHitCount;
        repeated_provider_call_prevented_count = $RepeatedProviderPreventedCount;
        no_minute_probe = $true;
        no_intraday_metrics = $true;
        no_vwap = $true;
        no_trading_advice = $true;
    })
})
$Manifest | ConvertTo-Json -Depth 8 | Set-Content $ManifestPath -Encoding UTF8

$PipelineLayerManifest = New-Object PSObject -Property ([ordered]@{
    account = 'energy';
    pipeline_name = 'energy_research_pipeline';
    version = 'v0.7.5';
    generated_at = $GeneratedAt;
    layer_mismatch_count = $LayerMismatchCount;
    layers = @($LayerManifests);
})
$PipelineLayerManifest | ConvertTo-Json -Depth 8 | Set-Content $LayerManifestPath -Encoding UTF8

$UploadLines = @(
    '# Energy Research Pipeline Upload Manifest',
    '',
    '## Core State',
    '- outputs_energy_latest/0_upload_bundle.md',
    '',
    '## Research Chain',
    '- outputs_energy_pipeline_latest/pipeline_summary.md',
    '- outputs_energy_scan_latest/0_upload_bundle.md',
    '- outputs_energy_watchlist_latest/0_upload_bundle.md',
    '- outputs_energy_operation_candidates_latest/0_upload_bundle.md',
    '- outputs_energy_latest/0_upload_bundle.md',
    '',
    '## Notes',
    '- Data and configuration status only.',
    '- No minute_probe, no intraday_metrics, no VWAP, no trading advice.'
)
$UploadLines | Set-Content $UploadManifestPath -Encoding UTF8

if ($null -ne $PreviousUseQuoteCache) {
    $env:MARKET_GUARD_USE_QUOTE_RUN_CACHE = $PreviousUseQuoteCache
} else {
    Remove-Item Env:\MARKET_GUARD_USE_QUOTE_RUN_CACHE -ErrorAction SilentlyContinue
}
if ($null -ne $PreviousQuoteCacheDir) {
    $env:MARKET_GUARD_QUOTE_RUN_CACHE_DIR = $PreviousQuoteCacheDir
} else {
    Remove-Item Env:\MARKET_GUARD_QUOTE_RUN_CACHE_DIR -ErrorAction SilentlyContinue
}

Write-Host ('Pipeline summary: ' + $SummaryPath)
if ($Failed -gt 0) {
    exit 1
}
exit 0
