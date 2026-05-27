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
$SnapshotRoot = Join-Path $OutputDir 'snapshots'

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
if (Test-Path $SnapshotRoot) {
    Remove-Item -Recurse -Force -LiteralPath $SnapshotRoot -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $SnapshotRoot | Out-Null
if (Test-Path $QuoteCacheDir) {
    Remove-Item -Recurse -Force -LiteralPath $QuoteCacheDir -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $QuoteCacheDir | Out-Null
$PipelineStartedAt = (Get-Date).ToUniversalTime()
$GeneratedAt = $PipelineStartedAt.ToString('o')
$PipelineRunId = [guid]::NewGuid().ToString()
$PreviousUseQuoteCache = $env:MARKET_GUARD_USE_QUOTE_RUN_CACHE
$PreviousQuoteCacheDir = $env:MARKET_GUARD_QUOTE_RUN_CACHE_DIR
$env:MARKET_GUARD_USE_QUOTE_RUN_CACHE = '1'
$env:MARKET_GUARD_QUOTE_RUN_CACHE_DIR = $QuoteCacheDir

function Get-FileHashSha256 {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return ''
    }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-StepRuntimeClassification {
    param(
        [string]$Status,
        [bool]$RuntimeWarning,
        [int]$ProviderTimeoutCount,
        [int]$ProviderCircuitOpenCount
    )
    if ($Status -eq 'failed') {
        return [PSCustomObject]@{ Level = 'failed'; Reason = 'command_failed_or_required_output_missing' }
    }
    if ($Status -eq 'strict_blocked_but_reported') {
        return [PSCustomObject]@{ Level = 'strict_blocked_but_reported'; Reason = 'strict_blocked_with_reports' }
    }
    if ($RuntimeWarning) {
        return [PSCustomObject]@{ Level = 'soft_budget_exceeded'; Reason = 'step_elapsed_exceeded_soft_runtime_budget' }
    }
    if ($ProviderCircuitOpenCount -gt 0) {
        return [PSCustomObject]@{ Level = 'provider_circuit_open'; Reason = 'provider_circuit_open_reported' }
    }
    if ($ProviderTimeoutCount -gt 0) {
        return [PSCustomObject]@{ Level = 'provider_timeout'; Reason = 'provider_timeout_reported' }
    }
    return [PSCustomObject]@{ Level = 'runtime_info'; Reason = 'within_runtime_policy' }
}

function Copy-PipelineStepSnapshot {
    param(
        [hashtable]$Step,
        [PSCustomObject]$Result,
        [string]$PipelineRunId,
        [string]$SnapshotRoot,
        [string]$ProjectRoot
    )
    $StepOutputPath = Join-Path $ProjectRoot $Step['OutputDir']
    $StepSnapshotDir = Join-Path $SnapshotRoot $Step['Name']
    New-Item -ItemType Directory -Force -Path $StepSnapshotDir | Out-Null
    $FilesToCopy = @(
        'layer_manifest.json',
        'data_completeness_report.md',
        'runtime_diagnostics.md',
        'provider_health_report.md',
        '0_upload_bundle.md',
        'prices_snapshot.csv',
        'debug_bundle.md',
        'index.md',
        'scan_universe_report.md',
        'candidate_watchlist_report.md',
        'operation_candidate_report.md',
        'energy_price_block.md'
    )
    $CopiedFiles = @()
    foreach ($FileName in $FilesToCopy) {
        $SourcePath = Join-Path $StepOutputPath $FileName
        if (Test-Path $SourcePath) {
            Copy-Item -LiteralPath $SourcePath -Destination (Join-Path $StepSnapshotDir $FileName) -Force
            $CopiedFiles += $FileName
        }
    }
    $LayerManifestSnapshotPath = Join-Path $StepSnapshotDir 'layer_manifest.json'
    $PricesSnapshotPath = Join-Path $StepSnapshotDir 'prices_snapshot.csv'
    $UploadBundlePath = Join-Path $StepSnapshotDir '0_upload_bundle.md'
    $Metadata = [ordered]@{
        pipeline_run_id = $PipelineRunId
        source_run_id = $PipelineRunId
        step_name = $Step['Name']
        account = 'energy'
        generated_at = $Result.finished_at
        output_dir = $Step['OutputDir']
        step_output_dir = $Step['OutputDir']
        snapshot_dir = $StepSnapshotDir
        step_snapshot_dir = $StepSnapshotDir
        status = $Result.status
        exit_code = $Result.exit_code
        elapsed_seconds = $Result.elapsed_seconds
        copied_files = $CopiedFiles
        layer_manifest_path = $LayerManifestSnapshotPath
        layer_manifest_hash_sha256 = Get-FileHashSha256 $LayerManifestSnapshotPath
        prices_snapshot_hash_sha256 = Get-FileHashSha256 $PricesSnapshotPath
        upload_bundle_hash_sha256 = Get-FileHashSha256 $UploadBundlePath
    }
    $MetadataPath = Join-Path $StepSnapshotDir 'snapshot_metadata.json'
    $Metadata | ConvertTo-Json -Depth 6 | Set-Content $MetadataPath -Encoding UTF8
    $Metadata['snapshot_metadata_path'] = $MetadataPath
    $Metadata['snapshot_metadata_hash_sha256'] = Get-FileHashSha256 $MetadataPath
    return [PSCustomObject]$Metadata
}

$Steps = @(
    @{ Name = 'energy_scan'; Script = 'run_energy_scan.ps1'; Args = [string[]]@('-Mode', $ScanMode); OutputDir = 'outputs_energy_scan_latest'; Skip = $SkipScan.IsPresent },
    @{ Name = 'energy_watchlist'; Script = 'run_energy_watchlist.ps1'; OutputDir = 'outputs_energy_watchlist_latest'; Skip = $SkipWatchlist.IsPresent },
    @{ Name = 'energy_operation_candidates'; Script = 'run_energy_operation_candidates.ps1'; OutputDir = 'outputs_energy_operation_candidates_latest'; Skip = $SkipOperationCandidates.IsPresent },
    @{ Name = 'energy_fast_strict'; Script = 'run_energy_fast_strict.ps1'; OutputDir = 'outputs_energy_latest'; Skip = $SkipEnergyFast.IsPresent }
)

$Results = @()
$SnapshotEntries = @()
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
            runtime_warning_level = 'runtime_info'
            runtime_warning_reason = 'skipped_by_parameter'
            max_run_seconds = ''
            snapshot_dir = ''
            snapshot_metadata_path = ''
            source_run_id = $PipelineRunId
            generated_at = ''
            layer_manifest_path = ''
            layer_manifest_hash_sha256 = ''
            prices_snapshot_hash_sha256 = ''
            upload_bundle_hash_sha256 = ''
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
    $ProviderTimeoutCount = 0
    $ProviderCircuitOpenCount = 0
    if (Test-Path $RuntimePath) {
        if ($RuntimeContent -match 'provider_timeout_count:\s*(\d+)') { $ProviderTimeoutCount = [int]$Matches[1] }
        if ($RuntimeContent -match 'provider_circuit_open_count:\s*(\d+)') { $ProviderCircuitOpenCount = [int]$Matches[1] }
    }
    $RuntimeClassification = Get-StepRuntimeClassification -Status $Status -RuntimeWarning $RuntimeWarning -ProviderTimeoutCount $ProviderTimeoutCount -ProviderCircuitOpenCount $ProviderCircuitOpenCount
    $Result = [PSCustomObject]@{
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
        runtime_warning_level = $RuntimeClassification.Level
        runtime_warning_reason = $RuntimeClassification.Reason
        max_run_seconds = $MaxRunSeconds
        snapshot_dir = ''
        snapshot_metadata_path = ''
        source_run_id = $PipelineRunId
        generated_at = $FinishedAt.ToString('o')
        layer_manifest_path = ''
        layer_manifest_hash_sha256 = ''
        prices_snapshot_hash_sha256 = ''
        upload_bundle_hash_sha256 = ''
    }
    $SnapshotEntry = Copy-PipelineStepSnapshot -Step $Step -Result $Result -PipelineRunId $PipelineRunId -SnapshotRoot $SnapshotRoot -ProjectRoot $ProjectRoot
    $Result.snapshot_dir = $SnapshotEntry.step_snapshot_dir
    $Result.snapshot_metadata_path = $SnapshotEntry.snapshot_metadata_path
    $Result.layer_manifest_path = $SnapshotEntry.layer_manifest_path
    $Result.layer_manifest_hash_sha256 = $SnapshotEntry.layer_manifest_hash_sha256
    $Result.prices_snapshot_hash_sha256 = $SnapshotEntry.prices_snapshot_hash_sha256
    $Result.upload_bundle_hash_sha256 = $SnapshotEntry.upload_bundle_hash_sha256
    $Results += $Result
    $SnapshotEntries += $SnapshotEntry
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
$RuntimeWarningCount = @($Results | Where-Object { $_.runtime_warning_level -notin @('runtime_info', 'strict_blocked_but_reported') }).Count

$LayerManifests = @()
$CompletenessRows = @()
foreach ($Step in $Steps) {
    $StepResult = $Results | Where-Object { $_.name -eq $Step['Name'] } | Select-Object -First 1
    $StepOutputPath = if ($StepResult -and $StepResult.snapshot_dir) { $StepResult.snapshot_dir } else { Join-Path $ProjectRoot $Step['OutputDir'] }
    $StepLayerManifestPath = Join-Path $StepOutputPath 'layer_manifest.json'
    if (Test-Path $StepLayerManifestPath) {
        try {
            $LayerData = Get-Content $StepLayerManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $LayerData | Add-Member -NotePropertyName pipeline_run_id -NotePropertyValue $PipelineRunId -Force
            $LayerData | Add-Member -NotePropertyName source_run_id -NotePropertyValue $PipelineRunId -Force
            $LayerData | Add-Member -NotePropertyName snapshot_dir -NotePropertyValue $StepOutputPath -Force
            $LayerData | Add-Member -NotePropertyName layer_manifest_path -NotePropertyValue $StepLayerManifestPath -Force
            $LayerData | Add-Member -NotePropertyName layer_manifest_hash_sha256 -NotePropertyValue (Get-FileHashSha256 $StepLayerManifestPath) -Force
            $LayerManifests += $LayerData
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
                pipeline_run_id = $PipelineRunId
                source_run_id = $PipelineRunId
                snapshot_dir = $StepOutputPath
                layer_manifest_path = $StepLayerManifestPath
                layer_manifest_hash_sha256 = ''
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
            pipeline_run_id = $PipelineRunId
            source_run_id = $PipelineRunId
            snapshot_dir = $StepOutputPath
            layer_manifest_path = $StepLayerManifestPath
            layer_manifest_hash_sha256 = ''
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
$Lines += ('- pipeline_run_id: ' + $PipelineRunId)
$Lines += ('- source_run_id: ' + $PipelineRunId)
$Lines += '- account: energy'
$Lines += '- pipeline_name: energy_research_pipeline'
$Lines += '- version: v0.7.5'
$Lines += ('- scan_mode: ' + $ScanMode)
$Lines += ('- total_steps: ' + $Results.Count)
$Lines += ('- passed: ' + $Passed)
$Lines += ('- strict_blocked_but_reported: ' + $StrictBlocked)
$Lines += ('- failed: ' + $Failed)
$Lines += ('- runtime_warnings: ' + $RuntimeWarningCount)
$Lines += ('- skipped_steps: ' + $Skipped)
$Lines += ('- total_elapsed_seconds: ' + $TotalElapsedSeconds)
$Lines += '- runtime_warning_policy: runtime_info, runtime_warning, soft_budget_exceeded, hard_timeout, provider_timeout, provider_circuit_open, strict_blocked_but_reported, failed'
$Lines += '- runtime_warnings_do_not_equal_failed: true'
$Lines += '- no minute_probe'
$Lines += '- no intraday_metrics'
$Lines += '- no VWAP'
$Lines += '- no trading advice'
$Lines += ''
$Lines += '## Steps'
$Lines += ''
$Lines += '| step | status | exit_code | elapsed_seconds | runtime_warning_level | output_dir | snapshot_dir | generated_at | source_run_id | layer_manifest_hash | prices_snapshot_hash | upload_bundle_hash |'
$Lines += '|---|---|---:|---:|---|---|---|---|---|---|---|---|'
foreach ($Result in $Results) {
    $Lines += ('| ' + $Result.name + ' | ' + $Result.status + ' | ' + $Result.exit_code + ' | ' + $Result.elapsed_seconds + ' | ' + $Result.runtime_warning_level + ' | ' + $Result.output_dir + ' | ' + $Result.snapshot_dir + ' | ' + $Result.generated_at + ' | ' + $Result.source_run_id + ' | ' + $Result.layer_manifest_hash_sha256 + ' | ' + $Result.prices_snapshot_hash_sha256 + ' | ' + $Result.upload_bundle_hash_sha256 + ' |')
}
$Lines += ''
$Lines += '## Pipeline Output Snapshots'
$Lines += ''
$Lines += ('- snapshots_root: ' + $SnapshotRoot)
$Lines += '- snapshots are copied during this pipeline run and are not affected by later standalone layer runs.'
$Lines += ''
$Lines += '| step_name | account | output_dir | snapshot_dir | snapshot_metadata | layer_manifest_path | manifest_hash | source_run_id |'
$Lines += '|---|---|---|---|---|---|---|---|'
foreach ($Snapshot in $SnapshotEntries) {
    $Lines += ('| ' + $Snapshot.step_name + ' | ' + $Snapshot.account + ' | ' + $Snapshot.step_output_dir + ' | ' + $Snapshot.step_snapshot_dir + ' | ' + $Snapshot.snapshot_metadata_path + ' | ' + $Snapshot.layer_manifest_path + ' | ' + $Snapshot.layer_manifest_hash_sha256 + ' | ' + $Snapshot.source_run_id + ' |')
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
$Lines += '| step | runtime_warning_level | runtime_warning_reason | run_time_budget_exceeded | provider_timeout_count | skipped_by_runtime_budget | circuit_open_count |'
$Lines += '|---|---|---|---|---:|---:|---:|'
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
    $Lines += ('| ' + $Result.name + ' | ' + $Result.runtime_warning_level + ' | ' + $Result.runtime_warning_reason + ' | ' + $BudgetExceeded + ' | ' + $TimeoutCount + ' | ' + $SkippedBudget + ' | ' + $CircuitCount + ' |')
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
    pipeline_run_id = $PipelineRunId;
    source_run_id = $PipelineRunId;
    generated_at = $GeneratedAt;
    snapshots_root = $SnapshotRoot;
    scan_mode = $ScanMode;
    steps = @($Results);
    snapshot_steps = @($SnapshotEntries);
    layer_config_summary = @($LayerManifests);
    data_completeness_summary = @($CompletenessRows);
    summary = New-Object PSObject -Property ([ordered]@{
        passed = $Passed;
        failed = $Failed;
        strict_blocked_but_reported = $StrictBlocked;
        runtime_warnings = $RuntimeWarningCount;
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
    pipeline_run_id = $PipelineRunId;
    source_run_id = $PipelineRunId;
    generated_at = $GeneratedAt;
    snapshots_root = $SnapshotRoot;
    layer_mismatch_count = $LayerMismatchCount;
    snapshot_steps = @($SnapshotEntries);
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
