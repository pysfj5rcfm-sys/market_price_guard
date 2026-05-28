# Operation Data Source Feasibility Matrix

Version: v0.7.5.4

Scope classification: operation data source feasibility matrix and readiness-tier design.

This document defines source roles and feasibility only. It does not alter current provider runtime, strict, usable_for_operation, quote_trust_tier, config, or pipeline behavior.

## Decision Summary

| source | recommended role | decision | blocking reason |
|---|---|---|---|
| Eastmoney Direct | fast_reference / reference_primary / legacy_operation_input | keep current provider; not operation_primary | public interface, no formal SLA, environment and endpoint risk |
| AKShare | broad_reference / batch_fallback / legacy_operation_input | keep current provider; not operation_primary | broad but heavy, upstream drift, intraday stability risk |
| yfinance | global_reference / US-HK fallback | keep current provider; not A-share operation_primary | limited A-share ETF suitability |
| mock | development_fallback only | keep only for development fallback | synthetic data, not trusted |
| Guosen iQuant | manual_verification_source / internal_strategy_platform_candidate | not automated_provider | not externally callable and not bridgeable under current broker response |
| QMT / miniQMT | first-priority feasibility target | investigate first | external Python bridge must be verified |
| PTrade | second-priority feasibility target | investigate after QMT | external API and file/localhost bridge must be verified |
| broker external quote API | feasibility target | investigate with broker | permission, field, and latency terms unknown |
| Wind / Choice | commercial_reference_or_operation_trial | evaluate if budget permits | license and integration cost |
| JQData / RQData | research_reference_or_operation_trial | evaluate for field and latency fit | realtime field completeness may vary |
| Tushare Pro | research_reference | not operation_primary by default | realtime suitability and latency limits |
| iTick / WebSocket realtime API | third-priority feasibility target | trial if broker APIs fail | vendor stability and field fit must be proven |
| Sina / Tencent / other free public endpoints | emergency_reference_fallback | do not promote | public endpoint risk and incomplete fields |
| manual verification source | manual_verification_source | keep outside automation | human copy path cannot be operation_primary |

## Matrix

| provider_name | provider_type | candidate_role | external_callable | bridgeable | can_write_local_file | can_push_localhost | supports_a_share | supports_etf | supports_hk | supports_us | supports_bid_ask | supports_minute_bar | supports_quote_time | supports_trading_status | expected_latency | stability_score | field_completeness_score | integration_cost_score | permission_cost_score | operation_primary_score | recommended_role | decision | next_action | blocking_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|---|
| Eastmoney Direct | public_reference_endpoint | current_provider | yes | yes | yes | no | yes | yes | limited | no | partial | partial | yes | partial | low | 3 | 3 | 1 | 1 | 2 | fast_reference / reference_primary / legacy_operation_input | keep_current_not_operation_primary | preserve current route; monitor health | public interface; no formal SLA; endpoint and permission risk |
| AKShare | wrapper_reference_library | current_provider | yes | yes | yes | no | yes | yes | partial | partial | partial | partial | partial | partial | medium_high | 3 | 3 | 1 | 1 | 2 | broad_reference / batch_fallback / legacy_operation_input | keep_current_not_operation_primary | preserve current route; monitor batch health | broad but heavy; upstream drift; intraday stability risk |
| yfinance | global_reference_library | current_provider | yes | yes | yes | no | no | partial | partial | yes | partial | yes | partial | partial | medium | 3 | 2 | 1 | 1 | 1 | global_reference / US-HK fallback | keep_current_not_a_share_operation_primary | preserve global reference role | not suitable as A-share ETF main operation source |
| mock | synthetic_development_source | current_development_fallback | yes | yes | yes | no | synthetic | synthetic | synthetic | synthetic | no | no | synthetic | no | low | 1 | 1 | 1 | 1 | 0 | development_fallback only | never_reference_or_operation | keep for tests only | synthetic and untrusted |
| Guosen iQuant | broker_internal_platform | broker_internal_quote_platform | no | no | no | unknown | yes | yes | yes | unknown | yes | yes | yes | likely | low_inside_platform | 4 | 4 | 5 | 3 | 0 | manual_verification_source / internal_strategy_platform_candidate | not_automated_provider | ask only bridge/export questions | strong internal quotes but not externally callable or bridgeable |
| QMT / miniQMT | broker_terminal_api | operation_primary_candidate | likely | likely | likely | likely | yes | yes | partial | no | likely | likely | likely | likely | low | 4 | 4 | 3 | 3 | 5 | first-priority feasibility target | spike_first | verify external Python API, local bridge, fields, latency | feasibility unverified in current repo |
| PTrade | broker_strategy_api | operation_primary_candidate | unknown | likely | unknown | unknown | yes | yes | partial | no | likely | likely | likely | likely | low | 4 | 4 | 3 | 3 | 4 | second-priority feasibility target | spike_after_qmt | verify external API, export path, and field coverage | feasibility unverified in current repo |
| broker external quote API | broker_api | operation_primary_candidate | unknown | unknown | unknown | unknown | likely | likely | possible | possible | possible | possible | likely | possible | low | 4 | 4 | 4 | 4 | 4 | broker_external_api_feasibility_target | investigate | request API, SDK, DLL, or local service details | access and terms unknown |
| Wind / Choice | commercial_market_data | commercial_trial_candidate | yes | yes | yes | possible | yes | yes | yes | yes | yes | yes | yes | likely | low | 5 | 5 | 4 | 5 | 4 | commercial_reference_or_operation_trial | evaluate_if_budget_permits | request realtime quote trial and field map | license and cost |
| JQData / RQData | quant_data_service | research_reference_or_operation_trial | yes | yes | yes | possible | yes | yes | limited | limited | possible | yes | yes | possible | medium | 4 | 3 | 3 | 3 | 3 | research_reference_or_operation_trial | evaluate_later | verify realtime depth and trading_status | realtime completeness may vary |
| Tushare Pro | data_service | research_reference | yes | yes | yes | possible | yes | yes | limited | limited | no | yes | partial | partial | medium_high | 3 | 2 | 2 | 2 | 1 | research_reference | not_operation_primary_by_default | use only if field freshness fits reference | realtime suitability limited |
| iTick / WebSocket realtime API | commercial_realtime_api | operation_primary_candidate | yes | yes | yes | yes | likely | likely | likely | likely | likely | likely | yes | possible | low | 4 | 4 | 3 | 3 | 4 | third-priority feasibility target | trial_after_broker_api_check | run quote trial and health report design | vendor fit unproven |
| Sina / Tencent / other free public endpoints | free_public_endpoint | emergency_reference_fallback | yes | yes | yes | no | yes | yes | partial | no | partial | partial | partial | partial | low_medium | 2 | 2 | 2 | 1 | 1 | emergency_reference_fallback | do_not_promote | keep outside operation_primary | public endpoint risk and incomplete fields |
| manual verification source | human_reference | manual_verification_source | no | no | no | no | yes | yes | yes | possible | possible | possible | possible | possible | human_speed | 3 | 3 | 1 | 1 | 0 | manual_verification_source | not_automated_provider | keep as manual cross-check only | not automatic ingest |

## Current Provider Roles

| provider | role |
|---|---|
| Eastmoney Direct | fast_reference / reference_primary / legacy_operation_input |
| AKShare | broad_reference / batch_fallback / legacy_operation_input |
| yfinance | global_reference / US-HK fallback |
| mock | development_fallback only |

None of Eastmoney Direct, AKShare, yfinance, or mock is designated as operation_primary in v0.7.5.4.

## Readiness Tier Mapping

| tier | meaning | status in v0.7.5.4 |
|---|---|---|
| full_operation | operation_primary succeeds with full fields | design only |
| conditional_operation | multiple reference providers succeed and cross-check | design only; no hard gate |
| legacy_operation | current provider passes current strict and usable_for_operation rules | protected |
| reference_only | price reference is useful but not operation-grade | unchanged |
| blocked | unusable due to mock, stale, missing, timeout, unsupported, untrusted, no quote_time, or no last_price | unchanged |

No dual-source hard gate is enabled. No current legacy operation path is downgraded by this matrix.

## Next Feasibility Order

| rank | target | action |
|---:|---|---|
| 1 | QMT / miniQMT | external Python API feasibility check |
| 2 | PTrade | external API feasibility check |
| 3 | Commercial realtime API | quote trial |
| 4 | Guosen iQuant | remain manual verification only unless external or bridge export becomes available |

No trading advice generated. operation_candidate is not an execution layer. watchlist is not an execution layer. scan is not a signal layer. This document is data source feasibility only.
