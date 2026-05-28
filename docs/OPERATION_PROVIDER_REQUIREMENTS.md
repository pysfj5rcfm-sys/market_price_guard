# Operation Provider Requirements

Version: v0.7.5.4

Scope classification: operation data source feasibility matrix and readiness-tier design.

This version is documentation-only for runtime behavior. It does not change provider_router, strict, usable_for_operation, quote_trust_tier, config, exit codes, or pipeline output semantics.

## Current Provider Positioning

| provider | current role | explicit boundary |
|---|---|---|
| Eastmoney Direct | fast_reference / reference_primary / legacy_operation_input | not operation_primary |
| AKShare | broad_reference / batch_fallback / legacy_operation_input | not operation_primary |
| yfinance | global_reference / US-HK fallback | not A-share operation_primary |
| mock | development_fallback only | never reference, never operation |

Eastmoney Direct remains the fast A-share and ETF reference path for current pipelines. It can continue as legacy operation input, but public-interface nature, no formal SLA, network permission risk, endpoint drift, anti-scrape risk, and environment limits keep it outside long-run operation_primary scope.

AKShare remains broad coverage for scan, watchlist, batch fallback, and research layers. It can continue as legacy operation input, but broad upstream wrappers, heavier runtime, upstream drift, and intraday stability limits keep it outside long-run operation_primary scope.

yfinance remains global reference for QQQ, US instruments, selected HK references, and non-A-share context. It is not suitable as the main A-share ETF operation source.

mock remains development_fallback only. It must never become usable_for_reference or usable_for_operation.

## operation_primary Admission Rules

An operation_primary source must meet all hard requirements below:

| requirement | rule |
|---|---|
| callable | externally callable, or at least bridgeable into market_price_guard |
| automatic ingest | market_price_guard can read it without human copy steps |
| not closed-only | not limited to a closed GUI or closed internal strategy runtime |
| core coverage | supports core symbols needed by tech and energy |
| quote_time | returns traceable quote_time |
| fetch_time | records fetch_time in guard runtime |
| last_price | returns latest price |
| latency | latency is controlled enough for operation checks |
| diagnostics | failures are diagnosable |
| health report | can enter provider_health_report |
| runtime report | can enter runtime_diagnostics |
| source trail | provider and source are traceable |

Preferred full-operation fields:

| field | status |
|---|---|
| bid1_price | preferred |
| ask1_price | preferred |
| bid1_volume | preferred |
| ask1_volume | preferred |
| volume | preferred |
| amount | preferred |
| trading_status | preferred |

## Operation Readiness Tiers

### full_operation

Definition: a true operation_primary source succeeds.

Admission conditions:

| condition | required |
|---|---|
| operation_primary provider success | yes |
| quote_time fresh | yes |
| fetch_time traceable | yes |
| last_price present | yes |
| bid1_price present | yes |
| ask1_price present | yes |
| bid1_volume present | yes |
| ask1_volume present | yes |
| volume present | yes |
| amount present | yes |
| trading_status present | yes |
| latency controlled | yes |
| provider_health normal | yes |
| source traceable | yes |

Candidate source families: QMT / miniQMT, PTrade, externally callable broker APIs, commercial realtime quote APIs, and other stable external sources with full field coverage.

Recommended field set:

| field |
|---|
| symbol |
| market |
| asset_type |
| quote_time |
| fetch_time |
| last_price |
| bid1_price |
| ask1_price |
| bid1_volume |
| ask1_volume |
| volume |
| amount |
| trading_status |
| provider |
| source |
| latency_ms |
| timezone |

### conditional_operation

Definition: no operation_primary source exists, but multiple reference providers succeed and cross-check within a future threshold.

Future admission example:

| condition | required |
|---|---|
| Eastmoney Direct success | yes |
| AKShare success | yes |
| price_diff within threshold | yes |
| quote_time and fetch_time fresh | yes |
| no stale state | yes |
| no mock | yes |
| minimum operation fields present | yes |

Minimum future field set:

| field |
|---|
| symbol |
| quote_time |
| fetch_time |
| last_price |
| volume or amount |
| provider |
| source |
| stale judgment |
| at least two independent reference providers cross-checked |

Important: v0.7.5.4 does not enable a dual-source hard gate. This tier is a future design only.

### legacy_operation

Definition: an existing provider passes the current strict and usable_for_operation rules even though it is not operation_primary.

Examples:

| example |
|---|
| AKShare succeeds alone under current rules |
| Eastmoney Direct succeeds alone under current rules |
| current strict permits operation |
| no_operation_primary_provider = true |
| cross_provider_confirmed = false |

Protection rule: legacy_operation preserves current pipeline usability. v0.7.5.4 must not downgrade a current passing path merely because it is not full_operation.

### reference_only

Definition: price is useful for research and reference, but not sufficient for operation.

Examples:

| example |
|---|
| single reference provider success |
| missing bid/ask depth |
| missing trading_status |
| weak quote_time |
| suitable for scan, watchlist, or operation_candidate only |
| not suitable for operation |

Minimum field set:

| field |
|---|
| symbol |
| last_price |
| provider |
| source |
| fetch_time |
| stale risk disclosure |

### blocked

Definition: not usable for reference or operation.

Blocked examples:

| reason |
|---|
| mock |
| stale |
| missing |
| timeout |
| unsupported |
| untrusted |
| no quote_time |
| no last_price |

## Non-Changes In v0.7.5.4

| area | statement |
|---|---|
| dual-source hard gate | not enabled |
| usable_for_operation | unchanged |
| strict | unchanged |
| quote_trust_tier | unchanged |
| provider_router | main routing logic unchanged |
| config | unchanged |
| pipeline behavior | unchanged |
| provider implementation | not included |
| trading logic | not included |

No trading advice generated. operation_candidate is not an execution layer. watchlist is not an execution layer. scan is not a signal layer. This document is data source feasibility only.
