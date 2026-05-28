# HANDOFF v0.7.5.4

Version: v0.7.5.4 | Operation Data Source Feasibility Matrix

Scope classification: operation data source feasibility matrix and readiness-tier design.

This version is not tech-only, not energy-only, not provider implementation, not provider expansion, not provider runtime hardening, not QDII premium, not commodity realtime framework, not trading logic, and not UI.

## Completed

- Created docs/OPERATION_PROVIDER_REQUIREMENTS.md.
- Created docs/OPERATION_DATA_SOURCE_FEASIBILITY_MATRIX.md.
- Created docs/IQUANT_FEASIBILITY_ASSESSMENT.md.
- Created scripts/build_operation_data_source_feasibility.ps1.
- Created outputs_operation_data_source_feasibility_latest with feasibility_matrix.csv, feasibility_matrix.json, feasibility_summary.md, and feasibility_summary.json.
- Created tests/test_operation_data_source_feasibility.py.
- Documented current provider roles, operation_readiness_tier design, iQuant feasibility, next source order, and non-change boundaries.

## Current Baselines

Tech current baseline:

| layer | count |
|---|---:|
| operation | 7 |
| operation_candidate | 19 |
| watchlist | 28 |
| scan | 40 |

Energy current baseline:

| layer | count |
|---|---:|
| operation | 4 |
| operation_candidate | 8 |
| watchlist | 24 |
| scan | 41 |

The old tech 7 / 11 / 16 / 30 baseline is historical only.

## Current Provider Positioning

| provider | role | explicit boundary |
|---|---|---|
| Eastmoney Direct | fast_reference / reference_primary / legacy_operation_input | not operation_primary |
| AKShare | broad_reference / batch_fallback / legacy_operation_input | not operation_primary |
| yfinance | global_reference / US-HK fallback | not A-share operation_primary |
| mock | development_fallback only | never reference, never operation |

## Operation Readiness Tiers

| tier | definition |
|---|---|
| full_operation | true operation_primary source succeeds with full field coverage |
| conditional_operation | multiple reference providers succeed and cross-check; future design only |
| legacy_operation | current providers pass existing strict and usable_for_operation rules |
| reference_only | useful for reference but not sufficient for operation |
| blocked | unusable due to mock, stale, missing, timeout, unsupported, untrusted, no quote_time, or no last_price |

## Legacy Operation Protection

legacy_operation protects current pipeline usability. v0.7.5.4 must not downgrade a current passing Eastmoney Direct or AKShare path only because there is no operation_primary provider yet.

## No Dual-Source Hard Gate

No dual-source hard gate is enabled in v0.7.5.4. conditional_operation is a future tier design only.

## iQuant Feasibility Conclusion

Guosen iQuant supports strong internal quote views, including ETF realtime ticks, ETF level-5 quote depth, and 00883.HK realtime quotes.

Guosen iQuant has strong internal quote capability but is not currently eligible as an automated market_price_guard provider because it is neither externally callable nor bridgeable under the broker's current response.

Current iQuant role: manual_verification_source / internal_strategy_platform_candidate. It does not enter provider_router and is not operation_primary.

Remaining broker questions:

| question |
|---|
| Is an internal strategy allowed to push HTTP POST or socket messages to localhost? |
| Does Guosen provide any external quote API, SDK, DLL, or local port service outside iQuant? |

## Feasibility Matrix Output

| output | path |
|---|---|
| matrix CSV | outputs_operation_data_source_feasibility_latest/feasibility_matrix.csv |
| matrix JSON | outputs_operation_data_source_feasibility_latest/feasibility_matrix.json |
| summary MD | outputs_operation_data_source_feasibility_latest/feasibility_summary.md |
| summary JSON | outputs_operation_data_source_feasibility_latest/feasibility_summary.json |

## Next Candidate Order

1. QMT / miniQMT external Python API feasibility check.
2. PTrade external API feasibility check.
3. Commercial realtime API quote trial.
4. iQuant remains manual verification only unless external or bridge export becomes available.

## Non-Changes

| area | statement |
|---|---|
| config | unchanged |
| strict | unchanged |
| usable_for_operation | unchanged |
| quote_trust_tier | unchanged |
| provider_router | main routing logic unchanged |
| provider implementation | not included |
| provider expansion | not included |
| trading logic | not included |
| QDII premium | not included |
| commodity realtime framework | not included |
| pipeline behavior | unchanged |

No trading advice generated. This version is data source feasibility only.

## Suggested Next Versions

| condition | suggested version |
|---|---|
| QMT / miniQMT is externally callable | v0.7.5.5 | QMT Operation Provider Spike |
| PTrade is externally callable | v0.7.5.5 | PTrade Operation Provider Spike |
| broker external APIs are not feasible | v0.7.5.5 | Commercial Realtime API Trial |
| no short-term operation_primary path | v0.7.6 | QDII Premium Framework |
| no short-term operation_primary path and energy priority rises | v0.7.6 | Energy Commodity Reference Framework |

Do not implement those items inside v0.7.5.4.

## Validation Commands

```powershell
pytest
.\scripts\check_account_layer_config.ps1 -Account tech
.\scripts\check_account_layer_config.ps1 -Account energy
.\scripts\build_operation_data_source_feasibility.ps1
Get-ChildItem outputs_operation_data_source_feasibility_latest
Get-Content outputs_operation_data_source_feasibility_latest\feasibility_summary.md -Encoding UTF8
Get-Content outputs_operation_data_source_feasibility_latest\feasibility_summary.json -Encoding UTF8
Get-Content docs\OPERATION_PROVIDER_REQUIREMENTS.md -Encoding UTF8
Get-Content docs\OPERATION_DATA_SOURCE_FEASIBILITY_MATRIX.md -Encoding UTF8
Get-Content docs\IQUANT_FEASIBILITY_ASSESSMENT.md -Encoding UTF8
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
Get-Content outputs_tech_pipeline_latest\pipeline_summary.md -Encoding UTF8
.\scripts\run_energy_research_pipeline.ps1
Get-Content outputs_energy_pipeline_latest\pipeline_summary.md -Encoding UTF8
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
.\scripts\run_uat.ps1 -Mode energy -UseRunCache
.\scripts\build_acceptance_summary.ps1
Get-Content outputs_acceptance_latest\acceptance_summary.md -Encoding UTF8
git diff -- config
git diff -- src/market_price_guard/provider_router.py
```

## Strict Prohibitions

- Do not enable a dual-source hard gate.
- Do not downgrade Eastmoney Direct or AKShare current legacy paths.
- Do not mark iQuant as automated_provider.
- Do not mark Eastmoney Direct, AKShare, yfinance, or mock as operation_primary.
- Do not change provider_router main logic.
- Do not change strict.
- Do not change usable_for_operation.
- Do not change quote_trust_tier.
- Do not change config.
- Do not change pipeline exit codes.
- Do not implement provider runtime changes.
- Do not implement trading logic.
- Do not implement QDII premium.
- Do not implement commodity realtime framework.

## Remaining Issues

- No operation_primary source is implemented.
- QMT / miniQMT external callable feasibility is unknown.
- PTrade external callable feasibility is unknown.
- Commercial realtime API trial is not started.
- iQuant remains manual verification only under current broker response.
- Current legacy provider stability risk remains.

## Next Thread Must Read

- docs/ACCOUNT_ARCHITECTURE.md
- docs/HANDOFF_v0.7.5.4.md
- docs/HANDOFF_v0.7.5.3.md
- docs/OPERATION_PROVIDER_REQUIREMENTS.md
- docs/OPERATION_DATA_SOURCE_FEASIBILITY_MATRIX.md
- docs/IQUANT_FEASIBILITY_ASSESSMENT.md
- outputs_operation_data_source_feasibility_latest/feasibility_summary.md
- outputs_acceptance_latest/acceptance_summary.md
- scripts/run_tech_research_pipeline.ps1
- scripts/run_energy_research_pipeline.ps1
- scripts/run_uat.ps1
