param()

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$OutputDir = Join-Path $ProjectRoot 'outputs_acceptance_latest'
$SummaryMdPath = Join-Path $OutputDir 'acceptance_summary.md'
$SummaryJsonPath = Join-Path $OutputDir 'acceptance_summary.json'
$GeneratedAt = (Get-Date).ToUniversalTime().ToString('o')

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return $null
    }
    try {
        return Get-Content $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Get-PipelineAcceptance {
    param(
        [string]$Account,
        [string]$DirName
    )
    $PipelineDir = Join-Path $ProjectRoot $DirName
    $ManifestPath = Join-Path $PipelineDir 'pipeline_manifest.json'
    $LayerManifestPath = Join-Path $PipelineDir 'pipeline_layer_manifest.json'
    $SummaryPath = Join-Path $PipelineDir 'pipeline_summary.md'
    $Manifest = Read-JsonFile $ManifestPath
    $LayerManifest = Read-JsonFile $LayerManifestPath
    $Failed = if ($Manifest -and $Manifest.summary) { [int]$Manifest.summary.failed } else { 1 }
    $StrictBlocked = if ($Manifest -and $Manifest.summary) { [int]$Manifest.summary.strict_blocked_but_reported } else { 0 }
    $RuntimeWarnings = if ($Manifest -and $Manifest.summary -and $null -ne $Manifest.summary.runtime_warnings) { [int]$Manifest.summary.runtime_warnings } else { 0 }
    $SnapshotPath = if ($Manifest -and $Manifest.snapshots_root) { [string]$Manifest.snapshots_root } else { Join-Path $PipelineDir 'snapshots' }
    $LayerMismatchCount = if ($LayerManifest -and $null -ne $LayerManifest.layer_mismatch_count) { [int]$LayerManifest.layer_mismatch_count } else { 1 }
    return [ordered]@{
        account = $Account
        passed = ($Failed -eq 0 -and $LayerMismatchCount -eq 0)
        failed_count = $Failed
        strict_blocked_but_reported_count = $StrictBlocked
        runtime_warnings = $RuntimeWarnings
        snapshot_path = $SnapshotPath
        pipeline_summary_path = $SummaryPath
        pipeline_manifest_path = $ManifestPath
        layer_manifest_path = $LayerManifestPath
        layer_config_mismatch = ($LayerMismatchCount -gt 0)
    }
}

function Get-UatAcceptance {
    $ManifestPath = Join-Path $ProjectRoot 'outputs_uat_latest/uat_run_manifest.json'
    $Manifest = Read-JsonFile $ManifestPath
    $Modes = [ordered]@{}
    foreach ($Mode in @('quick', 'intraday', 'energy')) {
        $ModeDir = Join-Path $ProjectRoot ('outputs_uat_latest/' + $Mode)
        $SummaryJsonPath = Join-Path $ModeDir 'outputs_uat_summary.json'
        $SummaryMdPath = Join-Path $ModeDir 'outputs_uat_summary.md'
        $Summary = Read-JsonFile $SummaryJsonPath
        $Failed = if ($Summary) { [int]$Summary.failed } else { 1 }
        $Modes[$Mode] = [ordered]@{
            status = if ($Failed -eq 0) { 'passed' } else { 'failed' }
            summary_md = $SummaryMdPath
            summary_json = $SummaryJsonPath
            exists = (Test-Path $SummaryMdPath) -and (Test-Path $SummaryJsonPath)
            timeout_seconds = if ($Summary) { $Summary.timeout_seconds } else { $null }
            soft_budget_seconds = if ($Summary) { $Summary.soft_budget_seconds } else { $null }
            hard_timeout_seconds = if ($Summary) { $Summary.hard_timeout_seconds } else { $null }
            timed_out = if ($Summary) { [bool]$Summary.timed_out } else { $false }
            runtime_budget_warning = if ($Summary) { $Summary.runtime_budget_warning } else { $null }
            failed = $Failed
            strict_blocked_but_reported = if ($Summary) { [int]$Summary.strict_blocked_but_reported } else { 0 }
        }
    }
    return [ordered]@{
        manifest_path = $ManifestPath
        latest_mode = if ($Manifest) { $Manifest.latest_mode } else { '' }
        modes = $Modes
    }
}

function Get-ConfigDiffStatus {
    Push-Location $ProjectRoot
    git diff --quiet -- config
    $ExitCode = $LASTEXITCODE
    Pop-Location
    return [ordered]@{
        expected = 'empty'
        status = if ($ExitCode -eq 0) { 'empty' } else { 'non_empty' }
        passed = ($ExitCode -eq 0)
    }
}

function Get-NoAdviceScan {
    $Paths = @(
        (Join-Path $ProjectRoot 'outputs_acceptance_latest/*.md'),
        (Join-Path $ProjectRoot 'outputs_energy_pipeline_latest/*.md'),
        (Join-Path $ProjectRoot 'outputs_energy_pipeline_latest/snapshots/*/*.md'),
        (Join-Path $ProjectRoot 'outputs_tech_pipeline_latest/*.md'),
        (Join-Path $ProjectRoot 'outputs_tech_pipeline_latest/snapshots/*/*.md'),
        (Join-Path $ProjectRoot 'outputs_uat_latest/*/*.md')
    )
    $Pattern = '买入|卖出|加仓|减仓|做T|挂单|目标价|入场价|止损|preferred_action|action_hint|buy|sell|add|reduce'
    $ExistingPaths = @($Paths | Where-Object { Test-Path $_ })
    $Hits = if ($ExistingPaths.Count -gt 0) {
        @(Select-String -Path $ExistingPaths -Pattern $Pattern -CaseSensitive:$false -ErrorAction SilentlyContinue)
    } else {
        @()
    }
    return [ordered]@{
        status = if ($Hits.Count -eq 0) { 'passed' } else { 'failed' }
        hit_count = $Hits.Count
        hits = @($Hits | Select-Object -First 20 | ForEach-Object { $_.Path + ':' + $_.LineNumber + ':' + $_.Line.Trim() })
    }
}

function Get-UniverseSymbolCount {
    param([string]$RelativePath)
    $Path = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path $Path)) {
        return 0
    }
    $InSymbols = $false
    $Count = 0
    foreach ($Line in Get-Content $Path -Encoding UTF8) {
        if ($Line -match '^symbols:\s*$') {
            $InSymbols = $true
            continue
        }
        if ($InSymbols -and $Line -match '^\S' -and $Line -notmatch '^\s*-\s+') {
            break
        }
        if ($InSymbols -and $Line -match '^\s*-\s+\S+') {
            $Count += 1
        }
    }
    return $Count
}

function Get-AccountBaseline {
    param([string]$Account)
    if ($Account -eq 'tech') {
        return [ordered]@{
            operation = Get-UniverseSymbolCount 'config/universes/tech_core.yaml'
            operation_candidate = Get-UniverseSymbolCount 'config/universes/tech_operation_candidates.yaml'
            watchlist = Get-UniverseSymbolCount 'config/universes/tech_watchlist.yaml'
            scan = Get-UniverseSymbolCount 'config/universes/tech_scan_ai.yaml'
        }
    }
    return [ordered]@{
        operation = Get-UniverseSymbolCount 'config/universes/energy_core.yaml'
        operation_candidate = Get-UniverseSymbolCount 'config/universes/energy_operation_candidates.yaml'
        watchlist = Get-UniverseSymbolCount 'config/universes/energy_watchlist.yaml'
        scan = Get-UniverseSymbolCount 'config/universes/energy_scan.yaml'
    }
}

$TechPipeline = Get-PipelineAcceptance -Account 'tech' -DirName 'outputs_tech_pipeline_latest'
$EnergyPipeline = Get-PipelineAcceptance -Account 'energy' -DirName 'outputs_energy_pipeline_latest'
$Uat = Get-UatAcceptance
$ConfigDiff = Get-ConfigDiffStatus
$NoAdviceScan = Get-NoAdviceScan
$TechBaseline = Get-AccountBaseline -Account 'tech'
$EnergyBaseline = Get-AccountBaseline -Account 'energy'

$Summary = [ordered]@{
    version = 'v0.7.5.3'
    generated_at = $GeneratedAt
    scope_classification = 'account-generic runtime/UAT acceptance polish'
    tech_baseline = $TechBaseline
    energy_baseline = $EnergyBaseline
    tech_pipeline = $TechPipeline
    energy_pipeline = $EnergyPipeline
    uat = $Uat
    config_diff_status = $ConfigDiff
    no_advice_scan = $NoAdviceScan
    unresolved_backlog = @(
        'tech scan_ai / minute_probe may exceed soft runtime budget',
        'energy operation provider coverage still weak',
        'QDII premium not implemented',
        'energy commodity reference not implemented'
    )
}

$Lines = @()
$Lines += '# Acceptance Summary'
$Lines += ''
$Lines += '- version: v0.7.5.3'
$Lines += ('- generated_at: ' + $GeneratedAt)
$Lines += '- scope_classification: account-generic runtime/UAT acceptance polish'
$Lines += ''
$Lines += '## Baselines'
$Lines += ''
$Lines += ('- tech: operation=' + $TechBaseline.operation + ', operation_candidate=' + $TechBaseline.operation_candidate + ', watchlist=' + $TechBaseline.watchlist + ', scan=' + $TechBaseline.scan)
$Lines += ('- energy: operation=' + $EnergyBaseline.operation + ', operation_candidate=' + $EnergyBaseline.operation_candidate + ', watchlist=' + $EnergyBaseline.watchlist + ', scan=' + $EnergyBaseline.scan)
$Lines += ''
$Lines += '## Tech Pipeline'
$Lines += ''
$Lines += ('- passed: ' + ([string]$TechPipeline.passed).ToLowerInvariant())
$Lines += ('- failed_count: ' + $TechPipeline.failed_count)
$Lines += ('- strict_blocked_but_reported_count: ' + $TechPipeline.strict_blocked_but_reported_count)
$Lines += ('- runtime_warnings: ' + $TechPipeline.runtime_warnings)
$Lines += ('- snapshot_path: ' + $TechPipeline.snapshot_path)
$Lines += ('- pipeline_summary_path: ' + $TechPipeline.pipeline_summary_path)
$Lines += ''
$Lines += '## Energy Pipeline'
$Lines += ''
$Lines += ('- passed: ' + ([string]$EnergyPipeline.passed).ToLowerInvariant())
$Lines += ('- failed_count: ' + $EnergyPipeline.failed_count)
$Lines += ('- strict_blocked_but_reported_count: ' + $EnergyPipeline.strict_blocked_but_reported_count)
$Lines += ('- runtime_warnings: ' + $EnergyPipeline.runtime_warnings)
$Lines += ('- snapshot_path: ' + $EnergyPipeline.snapshot_path)
$Lines += ('- pipeline_summary_path: ' + $EnergyPipeline.pipeline_summary_path)
$Lines += ''
$Lines += '## UAT'
$Lines += ''
foreach ($Mode in @('quick', 'intraday', 'energy')) {
    $ModeInfo = $Uat.modes[$Mode]
    $Lines += ('- ' + $Mode + ': status=' + $ModeInfo.status + '; summary_md=' + $ModeInfo.summary_md + '; timeout_seconds=' + $ModeInfo.timeout_seconds + '; soft_budget_seconds=' + $ModeInfo.soft_budget_seconds + '; hard_timeout_seconds=' + $ModeInfo.hard_timeout_seconds)
}
$Lines += ''
$Lines += '## Config Diff'
$Lines += ''
$Lines += ('- expected: ' + $ConfigDiff.expected)
$Lines += ('- status: ' + $ConfigDiff.status)
$Lines += ''
$Lines += '## No Advice Scan'
$Lines += ''
$Lines += ('- status: ' + $NoAdviceScan.status)
$Lines += ('- hit_count: ' + $NoAdviceScan.hit_count)
$Lines += ''
$Lines += '## Unresolved Backlog'
$Lines += ''
foreach ($Item in $Summary.unresolved_backlog) {
    $Lines += ('- ' + $Item)
}

$Lines | Set-Content $SummaryMdPath -Encoding UTF8
$Summary | ConvertTo-Json -Depth 10 | Set-Content $SummaryJsonPath -Encoding UTF8

Write-Host ('Acceptance summary: ' + $SummaryMdPath)
Write-Host ('Acceptance summary JSON: ' + $SummaryJsonPath)
exit 0
