param()

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$OutputDir = Join-Path $ProjectRoot 'outputs_operation_data_source_feasibility_latest'
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$Version = 'v0.7.5.4'
$Scope = 'operation data source feasibility matrix and readiness-tier design'
$GeneratedAt = (Get-Date).ToUniversalTime().ToString('o')

$Matrix = @(
    [ordered]@{ provider_name = 'Eastmoney Direct'; provider_type = 'public_reference_endpoint'; candidate_role = 'current_provider'; external_callable = 'yes'; bridgeable = 'yes'; can_write_local_file = 'yes'; can_push_localhost = 'no'; supports_a_share = 'yes'; supports_etf = 'yes'; supports_hk = 'limited'; supports_us = 'no'; supports_bid_ask = 'partial'; supports_minute_bar = 'partial'; supports_quote_time = 'yes'; supports_trading_status = 'partial'; expected_latency = 'low'; stability_score = 3; field_completeness_score = 3; integration_cost_score = 1; permission_cost_score = 1; operation_primary_score = 2; recommended_role = 'fast_reference / reference_primary / legacy_operation_input'; decision = 'keep_current_not_operation_primary'; next_action = 'preserve current route; monitor health'; blocking_reason = 'public interface; no formal SLA; endpoint and permission risk' }
    [ordered]@{ provider_name = 'AKShare'; provider_type = 'wrapper_reference_library'; candidate_role = 'current_provider'; external_callable = 'yes'; bridgeable = 'yes'; can_write_local_file = 'yes'; can_push_localhost = 'no'; supports_a_share = 'yes'; supports_etf = 'yes'; supports_hk = 'partial'; supports_us = 'partial'; supports_bid_ask = 'partial'; supports_minute_bar = 'partial'; supports_quote_time = 'partial'; supports_trading_status = 'partial'; expected_latency = 'medium_high'; stability_score = 3; field_completeness_score = 3; integration_cost_score = 1; permission_cost_score = 1; operation_primary_score = 2; recommended_role = 'broad_reference / batch_fallback / legacy_operation_input'; decision = 'keep_current_not_operation_primary'; next_action = 'preserve current route; monitor batch health'; blocking_reason = 'broad but heavy; upstream drift; intraday stability risk' }
    [ordered]@{ provider_name = 'yfinance'; provider_type = 'global_reference_library'; candidate_role = 'current_provider'; external_callable = 'yes'; bridgeable = 'yes'; can_write_local_file = 'yes'; can_push_localhost = 'no'; supports_a_share = 'no'; supports_etf = 'partial'; supports_hk = 'partial'; supports_us = 'yes'; supports_bid_ask = 'partial'; supports_minute_bar = 'yes'; supports_quote_time = 'partial'; supports_trading_status = 'partial'; expected_latency = 'medium'; stability_score = 3; field_completeness_score = 2; integration_cost_score = 1; permission_cost_score = 1; operation_primary_score = 1; recommended_role = 'global_reference / US-HK fallback'; decision = 'keep_current_not_a_share_operation_primary'; next_action = 'preserve global reference role'; blocking_reason = 'not suitable as A-share ETF main operation source' }
    [ordered]@{ provider_name = 'mock'; provider_type = 'synthetic_development_source'; candidate_role = 'current_development_fallback'; external_callable = 'yes'; bridgeable = 'yes'; can_write_local_file = 'yes'; can_push_localhost = 'no'; supports_a_share = 'synthetic'; supports_etf = 'synthetic'; supports_hk = 'synthetic'; supports_us = 'synthetic'; supports_bid_ask = 'no'; supports_minute_bar = 'no'; supports_quote_time = 'synthetic'; supports_trading_status = 'no'; expected_latency = 'low'; stability_score = 1; field_completeness_score = 1; integration_cost_score = 1; permission_cost_score = 1; operation_primary_score = 0; recommended_role = 'development_fallback only'; decision = 'never_reference_or_operation'; next_action = 'keep for tests only'; blocking_reason = 'synthetic and untrusted' }
    [ordered]@{ provider_name = 'Guosen iQuant'; provider_type = 'broker_internal_platform'; candidate_role = 'broker_internal_quote_platform'; external_callable = 'no'; bridgeable = 'no'; can_write_local_file = 'no'; can_push_localhost = 'unknown'; supports_a_share = 'yes'; supports_etf = 'yes'; supports_hk = 'yes'; supports_us = 'unknown'; supports_bid_ask = 'yes'; supports_minute_bar = 'yes'; supports_quote_time = 'yes'; supports_trading_status = 'likely'; expected_latency = 'low_inside_platform'; stability_score = 4; field_completeness_score = 4; integration_cost_score = 5; permission_cost_score = 3; operation_primary_score = 0; recommended_role = 'manual_verification_source / internal_strategy_platform_candidate'; decision = 'not_automated_provider'; next_action = 'ask only bridge/export questions'; blocking_reason = 'strong internal quotes but not externally callable or bridgeable' }
    [ordered]@{ provider_name = 'QMT / miniQMT'; provider_type = 'broker_terminal_api'; candidate_role = 'operation_primary_candidate'; external_callable = 'likely'; bridgeable = 'likely'; can_write_local_file = 'likely'; can_push_localhost = 'likely'; supports_a_share = 'yes'; supports_etf = 'yes'; supports_hk = 'partial'; supports_us = 'no'; supports_bid_ask = 'likely'; supports_minute_bar = 'likely'; supports_quote_time = 'likely'; supports_trading_status = 'likely'; expected_latency = 'low'; stability_score = 4; field_completeness_score = 4; integration_cost_score = 3; permission_cost_score = 3; operation_primary_score = 5; recommended_role = 'first-priority feasibility target'; decision = 'spike_first'; next_action = 'verify external Python API, local bridge, fields, latency'; blocking_reason = 'feasibility unverified in current repo' }
    [ordered]@{ provider_name = 'PTrade'; provider_type = 'broker_strategy_api'; candidate_role = 'operation_primary_candidate'; external_callable = 'unknown'; bridgeable = 'likely'; can_write_local_file = 'unknown'; can_push_localhost = 'unknown'; supports_a_share = 'yes'; supports_etf = 'yes'; supports_hk = 'partial'; supports_us = 'no'; supports_bid_ask = 'likely'; supports_minute_bar = 'likely'; supports_quote_time = 'likely'; supports_trading_status = 'likely'; expected_latency = 'low'; stability_score = 4; field_completeness_score = 4; integration_cost_score = 3; permission_cost_score = 3; operation_primary_score = 4; recommended_role = 'second-priority feasibility target'; decision = 'spike_after_qmt'; next_action = 'verify external API, export path, and field coverage'; blocking_reason = 'feasibility unverified in current repo' }
    [ordered]@{ provider_name = 'broker external quote API'; provider_type = 'broker_api'; candidate_role = 'operation_primary_candidate'; external_callable = 'unknown'; bridgeable = 'unknown'; can_write_local_file = 'unknown'; can_push_localhost = 'unknown'; supports_a_share = 'likely'; supports_etf = 'likely'; supports_hk = 'possible'; supports_us = 'possible'; supports_bid_ask = 'possible'; supports_minute_bar = 'possible'; supports_quote_time = 'likely'; supports_trading_status = 'possible'; expected_latency = 'low'; stability_score = 4; field_completeness_score = 4; integration_cost_score = 4; permission_cost_score = 4; operation_primary_score = 4; recommended_role = 'broker_external_api_feasibility_target'; decision = 'investigate'; next_action = 'request API, SDK, DLL, or local service details'; blocking_reason = 'access and terms unknown' }
    [ordered]@{ provider_name = 'Wind / Choice'; provider_type = 'commercial_market_data'; candidate_role = 'commercial_trial_candidate'; external_callable = 'yes'; bridgeable = 'yes'; can_write_local_file = 'yes'; can_push_localhost = 'possible'; supports_a_share = 'yes'; supports_etf = 'yes'; supports_hk = 'yes'; supports_us = 'yes'; supports_bid_ask = 'yes'; supports_minute_bar = 'yes'; supports_quote_time = 'yes'; supports_trading_status = 'likely'; expected_latency = 'low'; stability_score = 5; field_completeness_score = 5; integration_cost_score = 4; permission_cost_score = 5; operation_primary_score = 4; recommended_role = 'commercial_reference_or_operation_trial'; decision = 'evaluate_if_budget_permits'; next_action = 'request realtime quote trial and field map'; blocking_reason = 'license and cost' }
    [ordered]@{ provider_name = 'JQData / RQData'; provider_type = 'quant_data_service'; candidate_role = 'research_reference_or_operation_trial'; external_callable = 'yes'; bridgeable = 'yes'; can_write_local_file = 'yes'; can_push_localhost = 'possible'; supports_a_share = 'yes'; supports_etf = 'yes'; supports_hk = 'limited'; supports_us = 'limited'; supports_bid_ask = 'possible'; supports_minute_bar = 'yes'; supports_quote_time = 'yes'; supports_trading_status = 'possible'; expected_latency = 'medium'; stability_score = 4; field_completeness_score = 3; integration_cost_score = 3; permission_cost_score = 3; operation_primary_score = 3; recommended_role = 'research_reference_or_operation_trial'; decision = 'evaluate_later'; next_action = 'verify realtime depth and trading_status'; blocking_reason = 'realtime completeness may vary' }
    [ordered]@{ provider_name = 'Tushare Pro'; provider_type = 'data_service'; candidate_role = 'research_reference'; external_callable = 'yes'; bridgeable = 'yes'; can_write_local_file = 'yes'; can_push_localhost = 'possible'; supports_a_share = 'yes'; supports_etf = 'yes'; supports_hk = 'limited'; supports_us = 'limited'; supports_bid_ask = 'no'; supports_minute_bar = 'yes'; supports_quote_time = 'partial'; supports_trading_status = 'partial'; expected_latency = 'medium_high'; stability_score = 3; field_completeness_score = 2; integration_cost_score = 2; permission_cost_score = 2; operation_primary_score = 1; recommended_role = 'research_reference'; decision = 'not_operation_primary_by_default'; next_action = 'use only if field freshness fits reference'; blocking_reason = 'realtime suitability limited' }
    [ordered]@{ provider_name = 'iTick / WebSocket realtime API'; provider_type = 'commercial_realtime_api'; candidate_role = 'operation_primary_candidate'; external_callable = 'yes'; bridgeable = 'yes'; can_write_local_file = 'yes'; can_push_localhost = 'yes'; supports_a_share = 'likely'; supports_etf = 'likely'; supports_hk = 'likely'; supports_us = 'likely'; supports_bid_ask = 'likely'; supports_minute_bar = 'likely'; supports_quote_time = 'yes'; supports_trading_status = 'possible'; expected_latency = 'low'; stability_score = 4; field_completeness_score = 4; integration_cost_score = 3; permission_cost_score = 3; operation_primary_score = 4; recommended_role = 'third-priority feasibility target'; decision = 'trial_after_broker_api_check'; next_action = 'run quote trial and health report design'; blocking_reason = 'vendor fit unproven' }
    [ordered]@{ provider_name = 'Sina / Tencent / other free public endpoints'; provider_type = 'free_public_endpoint'; candidate_role = 'emergency_reference_fallback'; external_callable = 'yes'; bridgeable = 'yes'; can_write_local_file = 'yes'; can_push_localhost = 'no'; supports_a_share = 'yes'; supports_etf = 'yes'; supports_hk = 'partial'; supports_us = 'no'; supports_bid_ask = 'partial'; supports_minute_bar = 'partial'; supports_quote_time = 'partial'; supports_trading_status = 'partial'; expected_latency = 'low_medium'; stability_score = 2; field_completeness_score = 2; integration_cost_score = 2; permission_cost_score = 1; operation_primary_score = 1; recommended_role = 'emergency_reference_fallback'; decision = 'do_not_promote'; next_action = 'keep outside operation_primary'; blocking_reason = 'public endpoint risk and incomplete fields' }
    [ordered]@{ provider_name = 'manual verification source'; provider_type = 'human_reference'; candidate_role = 'manual_verification_source'; external_callable = 'no'; bridgeable = 'no'; can_write_local_file = 'no'; can_push_localhost = 'no'; supports_a_share = 'yes'; supports_etf = 'yes'; supports_hk = 'yes'; supports_us = 'possible'; supports_bid_ask = 'possible'; supports_minute_bar = 'possible'; supports_quote_time = 'possible'; supports_trading_status = 'possible'; expected_latency = 'human_speed'; stability_score = 3; field_completeness_score = 3; integration_cost_score = 1; permission_cost_score = 1; operation_primary_score = 0; recommended_role = 'manual_verification_source'; decision = 'not_automated_provider'; next_action = 'keep as manual cross-check only'; blocking_reason = 'not automatic ingest' }
)

$MatrixObjects = $Matrix | ForEach-Object { [PSCustomObject]$_ }
$MatrixObjects | Export-Csv -LiteralPath (Join-Path $OutputDir 'feasibility_matrix.csv') -NoTypeInformation -Encoding UTF8
$MatrixObjects | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $OutputDir 'feasibility_matrix.json') -Encoding UTF8

$Summary = [ordered]@{
    version = $Version
    generated_at = $GeneratedAt
    scope_classification = $Scope
    current_provider_roles = [ordered]@{
        eastmoney_direct = 'fast_reference / reference_primary / legacy_operation_input; not operation_primary'
        akshare = 'broad_reference / batch_fallback / legacy_operation_input; not operation_primary'
        yfinance = 'global_reference / US-HK fallback; not A-share operation_primary'
        mock = 'development_fallback only'
    }
    operation_readiness_tiers = @('full_operation', 'conditional_operation', 'legacy_operation', 'reference_only', 'blocked')
    iQuant_conclusion = 'Guosen iQuant has strong internal quote capability but is not currently eligible as an automated market_price_guard provider because it is neither externally callable nor bridgeable under the broker''s current response.'
    top_next_candidates = @(
        'QMT / miniQMT external Python API feasibility check'
        'PTrade external API feasibility check'
        'Commercial realtime API quote trial'
        'iQuant remains manual verification only unless external/bridge export becomes available'
    )
    blocked_candidates = @(
        'mock: development_fallback only'
        'Guosen iQuant: not automated_provider under current response'
        'manual verification source: not automatic ingest'
    )
    recommended_next_version = @(
        'v0.7.5.5 | QMT Operation Provider Spike if QMT / miniQMT is externally callable'
        'v0.7.5.5 | PTrade Operation Provider Spike if PTrade is externally callable'
        'v0.7.5.5 | Commercial Realtime API Trial if broker APIs are not feasible'
        'v0.7.6 | QDII Premium Framework or Energy Commodity Reference Framework if operation_primary is deferred'
    )
    no_pipeline_impact_statement = 'v0.7.5.4 does not change provider_router, strict, usable_for_operation, quote_trust_tier, config, exit codes, or pipeline behavior.'
    no_dual_source_hard_gate_statement = 'No dual-source hard gate is enabled in v0.7.5.4; conditional_operation is design-only.'
    no_trading_advice_statement = 'No trading advice generated; data source feasibility only.'
}

$Summary | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $OutputDir 'feasibility_summary.json') -Encoding UTF8

$Lines = @()
$Lines += '# Operation Data Source Feasibility Summary'
$Lines += ''
$Lines += ('- version: ' + $Version)
$Lines += ('- generated_at: ' + $GeneratedAt)
$Lines += ('- scope_classification: ' + $Scope)
$Lines += '- no_pipeline_impact: v0.7.5.4 does not change provider_router, strict, usable_for_operation, quote_trust_tier, config, exit codes, or pipeline behavior.'
$Lines += '- no_dual_source_hard_gate: No dual-source hard gate is enabled; conditional_operation is design-only.'
$Lines += '- no_trading_advice: No trading advice generated; data source feasibility only.'
$Lines += ''
$Lines += '## Current Provider Roles'
$Lines += ''
$Lines += '| provider | role |'
$Lines += '|---|---|'
$Lines += '| Eastmoney Direct | fast_reference / reference_primary / legacy_operation_input; not operation_primary |'
$Lines += '| AKShare | broad_reference / batch_fallback / legacy_operation_input; not operation_primary |'
$Lines += '| yfinance | global_reference / US-HK fallback; not A-share operation_primary |'
$Lines += '| mock | development_fallback only |'
$Lines += ''
$Lines += '## Operation Readiness Tiers'
$Lines += ''
$Lines += '| tier | status |'
$Lines += '|---|---|'
$Lines += '| full_operation | future operation_primary success tier |'
$Lines += '| conditional_operation | future cross-provider tier; no hard gate enabled |'
$Lines += '| legacy_operation | protected current path under existing strict and usable_for_operation rules |'
$Lines += '| reference_only | research/reference use only |'
$Lines += '| blocked | unusable due to mock, stale, missing, timeout, unsupported, untrusted, no quote_time, or no last_price |'
$Lines += ''
$Lines += '## iQuant Conclusion'
$Lines += ''
$Lines += 'Guosen iQuant has strong internal quote capability but is not currently eligible as an automated market_price_guard provider because it is neither externally callable nor bridgeable under the broker''s current response.'
$Lines += ''
$Lines += '## Top Next Candidates'
$Lines += ''
$Lines += '1. QMT / miniQMT external Python API feasibility check'
$Lines += '2. PTrade external API feasibility check'
$Lines += '3. Commercial realtime API quote trial'
$Lines += '4. iQuant remains manual verification only unless external/bridge export becomes available'
$Lines += ''
$Lines += '## Blocked Candidates'
$Lines += ''
$Lines += '- mock: development_fallback only'
$Lines += '- Guosen iQuant: not automated_provider under current response'
$Lines += '- manual verification source: not automatic ingest'
$Lines += ''
$Lines += '## Recommended Next Version'
$Lines += ''
$Lines += '- v0.7.5.5 | QMT Operation Provider Spike if QMT / miniQMT is externally callable'
$Lines += '- v0.7.5.5 | PTrade Operation Provider Spike if PTrade is externally callable'
$Lines += '- v0.7.5.5 | Commercial Realtime API Trial if broker APIs are not feasible'
$Lines += '- v0.7.6 | QDII Premium Framework or Energy Commodity Reference Framework if operation_primary is deferred'
$Lines += ''
$Lines += '## Matrix Path'
$Lines += ''
$Lines += '- feasibility_matrix.csv'
$Lines += '- feasibility_matrix.json'
$Lines += '- feasibility_summary.json'

$Lines -join [Environment]::NewLine | Set-Content (Join-Path $OutputDir 'feasibility_summary.md') -Encoding UTF8

Write-Host ('Generated operation data source feasibility outputs in ' + $OutputDir)
