# API Field Capability Matrix

## Purpose

This document audits the field capability of the current `market_price_guard` providers for tech-account intraday market checks.

This is a capability audit only. It is not trading advice, does not change strict, does not change provider trust tier, and does not mean a field is operation-grade. Operation use still depends on `quote_trust_tier`, `usable_for_operation`, strict, freshness, and provider health.

Naming conventions:

- Use `quote_purpose`, not a generic purpose field.
- Use `quote_trust_tier`, not a generic tier field.
- Prefer `selected_provider` when describing the final provider.
- Prefer `operation_blocking_reason` when describing operation blocking.
- Future `operation_permission` should be unified as `allowed_advice_level`.

## Current Providers

| provider | Current use | Trust position | Strength | Limitation | Operation fit | Reference fit | Scan/Reconcile fit |
|---|---|---|---|---|---|---|---|
| akshare | A-share, HK, ETF quote facts; ETF primary on operation tech path | operation when strict/freshness pass | ETF batch quote and timestamp support | A/H interfaces may be slow or fail; bid/ask and minute bars not standardized | yes, conditional on strict | yes | yes, especially diagnostic |
| eastmoney_direct | A-share/ETF direct quote candidate | reference / operation-candidate only | fast single-symbol quote path when reachable | unstable in current environment; not official exchange feed; no operation-grade promotion | no | yes when data valid | yes, for reconciliation diagnostics |
| yfinance | Secondary HK/A-share; tech ETF reference path | reference for ETFs; conditional existing behavior for some energy symbols | fast secondary public data | public Yahoo wrapper, not official exchange feed; precision/timestamp varies | conditional for existing non-ETF paths only | yes | yes |
| manual | GOLD_CNY manual price | operation when manual config and freshness pass | explicit user-entered timestamp and note | manual entry risk; fee/spread/settlement not automated | yes for configured manual assets | yes | not normal price reconciliation |
| mock | Development and offline tests | development | deterministic testing | not real market data | no | no for real decisions | tests only |

## Priority Levels

P0 required fields are the minimum needed for operation-grade price guarding and basic intraday data quality.

P1 strongly recommended fields improve intraday positioning, chase-risk checks, sector context, and conditional scanning.

P2 enhancement fields are useful for future ranking, advisory gating, QDII context, or portfolio-aware output, but do not block the current version.

## Field Capability Matrix

| Field | Priority | Current support status | API native support | Calculable from existing fields | Current provider/source | Refresh feature | Timestamp available | Operation use | Limitations | Alternative | Suggested version |
|---|---|---|---|---|---|---|---|---|---|---|---|
| symbol | P0 | supported | yes | no | PriceRecord / registry | per run | not applicable | yes | none | none | current |
| name | P0 | supported | yes | no | provider / registry | per run | not applicable | yes | provider names may differ | registry name | current |
| market | P0 | supported | yes | no | watchlist / registry | static | not applicable | yes | `CN` currently conflates country and exchange | future exchange field | v0.7.1.4 |
| asset_type | P0 | supported | no | no | symbol_registry | static | not applicable | yes | metadata only | registry update | current |
| quote_time | P0 | supported | provider_dependent | no | akshare / yfinance / eastmoney / manual | provider dependent | yes when provider supplies it | conditional | some providers may miss or use low precision | debug/provider health | current |
| provider / selected_provider | P0 | supported | guard-derived | no | provider_router | per run | not applicable | yes | final selected provider only | provider attempts in health report | current |
| source / function_name | P0 | supported | guard-derived | no | RawPrice diagnostics | per attempt | not applicable | yes | function_name coverage varies by provider | provider_health_report | current |
| fetch_time | P0 | supported | guard-derived | no | guard runtime | per fetch | yes | yes | local run-time only | runtime diagnostics | current |
| timezone | P0 | partially_supported | no | yes | freshness/provider parsing | static/rules | yes for parsed times | conditional | not a stable output column | quote_time UTC fields in diagnostics | v0.7.1.4 |
| trading_status | P0 | supported as market_status | guard-derived | yes | freshness | per run | yes via now | yes | simplified trading calendar | market_status | current |
| currency | P0 | supported | provider_dependent | defaultable | provider / manual | per quote | not applicable | yes | defaults can be assumed | reference_note | current |
| quote_purpose | P0 | supported | guard-derived | no | CLI/runtime | per run | not applicable | yes | none | none | current |
| quote_trust_tier | P0 | supported | guard-derived | no | normalize | per record | not applicable | yes | tier is not provider native | docs/output contract | current |
| usable_for_operation | P0 | supported | guard-derived | yes | normalize/strict | per record | not applicable | yes | depends on freshness and quality issues | blocking records | current |
| usable_for_reference | P0 | supported | guard-derived | yes | normalize | per record | not applicable | yes | reference does not imply operation | quote_trust_tier | current |
| confirmation_required | P0 | supported | guard-derived | yes | normalize | per record | not applicable | yes | does not change strict | operation_blocking_reason | current |
| blocking / blocking_records_count | P0 | supported | guard-derived | yes | completeness summary | per report | not applicable | yes | only strict required records block | data_completeness_report | current |
| blocking_reason / operation_blocking_reason | P0 | supported | guard-derived | yes | normalize/report | per record | not applicable | yes | maps from quality/freshness | stale_reason | current |
| strict / exit_code | P0 | supported | guard-derived | yes | main/runtime | per run | not applicable | yes | script environment can fail separately | index.md | current |
| stale_flag / is_stale | P0 | supported | guard-derived | yes | freshness | per record | yes | yes | needs valid quote_time | stale_reason | current |
| stale_seconds | P0 | partially_supported | no | yes | freshness diagnostics age_seconds | per record | yes | conditional | output column not standardized as stale_seconds | age_seconds diagnostics | v0.7.1.4 |
| provider_health | P0 | supported | guard-derived | yes | provider_health_report | per run | not applicable | yes | report text, not a scalar field | debug_bundle | current |
| runtime_summary | P0 | supported | guard-derived | yes | runtime_diagnostics | per run | yes | yes | runtime only | index/upload bundle | current |
| data_completeness_level | P0 | partially_supported | guard-derived | yes | completeness summary | per run | not applicable | conditional | not yet a single normalized enum | usable_for_operation plus reasons | v0.7.2 |
| last_price | P0 | supported as price | yes | no | akshare / yfinance / eastmoney / manual / mock | provider dependent | yes if quote_time valid | conditional | operation depends on tier/freshness | price | current |
| prev_close | P0 | partially_supported | provider_dependent | no | eastmoney f60 requested; akshare/yfinance may have | provider dependent | provider dependent | no | not standardized into PriceRecord/CSV | provider raw diagnostics later | v0.7.1.4 |
| open_price | P0 | partially_supported | provider_dependent | no | eastmoney f46 requested; akshare may have | provider dependent | provider dependent | no | not standardized | provider raw diagnostics later | v0.7.1.4 |
| high_price | P0 | partially_supported | provider_dependent | no | eastmoney f44 requested; akshare may have | provider dependent | provider dependent | no | not standardized | provider raw diagnostics later | v0.7.1.4 |
| low_price | P0 | partially_supported | provider_dependent | no | eastmoney f45 requested; akshare may have | provider dependent | provider dependent | no | not standardized | provider raw diagnostics later | v0.7.1.4 |
| bid1_price | P0 | missing | provider_dependent | no | not standardized | intraday/order book | provider dependent | no | Eastmoney may have fields but not requested/validated | skip until capability expansion | v0.7.1.5 |
| bid1_volume | P0 | missing | provider_dependent | no | not standardized | intraday/order book | provider dependent | no | not requested/validated | skip until capability expansion | v0.7.1.5 |
| ask1_price | P0 | missing | provider_dependent | no | not standardized | intraday/order book | provider dependent | no | not requested/validated | skip until capability expansion | v0.7.1.5 |
| ask1_volume | P0 | missing | provider_dependent | no | not standardized | intraday/order book | provider dependent | no | not requested/validated | skip until capability expansion | v0.7.1.5 |
| bid_ask_spread | P1 | planned | no | yes, needs bid1/ask1 | none | intraday | provider dependent | no | needs bid/ask | use caution flags only | v0.7.1.5 |
| volume | P0 | partially_supported | provider_dependent | no | eastmoney f47 requested; akshare may have | provider dependent | provider dependent | no | not standardized | future base quote fields | v0.7.1.4 |
| amount | P0 | partially_supported | provider_dependent | no | eastmoney f48 requested; akshare may have | provider dependent | provider dependent | no | not standardized | future base quote fields | v0.7.1.4 |
| turnover_rate | P1 | provider_dependent | provider_dependent | no | not standardized | provider dependent | provider dependent | no | requires provider field or float shares | volume proxy | v0.7.1.5 |
| price_change | P1 | partially_supported | provider_dependent | yes if last/prev close | eastmoney f169 requested | provider dependent | provider dependent | no | not standardized | calculate from last/prev_close later | v0.7.1.4 |
| price_change_pct | P1 | partially_supported | provider_dependent | yes if last/prev close | eastmoney f170 requested | provider dependent | provider dependent | no | not standardized | calculate later | v0.7.1.4 |
| amplitude_pct | P1 | calculable | no | yes, needs high/low/prev_close | none | intraday | provider dependent | no | base fields not standardized | future derivation | v0.7.1.6 |
| minute_bars | P0 | missing | provider_dependent | no | none | minute/intraday | yes if implemented | no | minute_bars / VWAP not developed | provider minute module | v0.7.3 |
| minute_bar_interval | P1 | missing | no | no | none | minute/intraday | not applicable | no | depends on minute_bars | configure with minute module | v0.7.3 |
| intraday_vwap | P0 | missing | no | yes, needs minute_bars amount/volume | none | intraday | yes if minute bars have time | no | minute_bars / VWAP not developed | intraday_avg_price if provider native | v0.7.3 |
| intraday_avg_price | P0 | missing | provider_dependent | yes | none | intraday | provider dependent | no | not standardized | VWAP later | v0.7.3 |
| cumulative_volume | P1 | partially_supported | provider_dependent | yes from minute bars or quote field | eastmoney f47 candidate | intraday | provider dependent | no | not standardized | volume later | v0.7.1.4 |
| cumulative_amount | P1 | partially_supported | provider_dependent | yes from minute bars or quote field | eastmoney f48 candidate | intraday | provider dependent | no | not standardized | amount later | v0.7.1.4 |
| recent_volume_5m | P1 | missing | no | yes, needs minute_bars | none | intraday | yes with minute bars | no | minute module missing | cumulative_volume proxy is insufficient | v0.7.3 |
| recent_amount_5m | P1 | missing | no | yes, needs minute_bars | none | intraday | yes with minute bars | no | minute module missing | cumulative_amount proxy is insufficient | v0.7.3 |
| recent_volume_15m | P1 | missing | no | yes, needs minute_bars | none | intraday | yes with minute bars | no | minute module missing | none | v0.7.3 |
| recent_amount_15m | P1 | missing | no | yes, needs minute_bars | none | intraday | yes with minute bars | no | minute module missing | none | v0.7.3 |
| day_position | P1 | calculable | no | yes, needs last/high/low | none | intraday | uses quote_time | future | high/low not standardized | basic derivation later | v0.7.1.6 |
| distance_to_vwap_pct | P1 | missing | no | yes, needs VWAP | none | intraday | yes with VWAP | no | VWAP missing | no safe substitute | v0.7.3 |
| drawdown_from_high_pct | P1 | calculable | no | yes, needs last/high | none | intraday | uses quote_time | future | high not standardized | derive after base fields | v0.7.1.6 |
| rebound_from_low_pct | P1 | calculable | no | yes, needs last/low | none | intraday | uses quote_time | future | low not standardized | derive after base fields | v0.7.1.6 |
| open_gap_pct | P1 | calculable | no | yes, needs open/prev_close | none | session | uses quote_time | future | open/prev_close not standardized | derive later | v0.7.1.6 |
| intraday_return_pct | P1 | calculable | no | yes, needs last/open | none | intraday | uses quote_time | future | open not standardized | derive later | v0.7.1.6 |
| vwap_support_flag | P1 | missing | no | yes, needs VWAP and price | none | intraday | yes with VWAP | no | VWAP missing | no safe substitute | v0.7.3 |
| near_high_flag | P1 | calculable | no | yes, needs high/last | none | intraday | uses quote_time | future | high not standardized | derive later | v0.7.1.6 |
| near_low_flag | P1 | calculable | no | yes, needs low/last | none | intraday | uses quote_time | future | low not standardized | derive later | v0.7.1.6 |
| far_above_vwap_flag | P1 | missing | no | yes, needs VWAP | none | intraday | yes with VWAP | no | VWAP missing | no safe substitute | v0.7.3 |
| pullback_confirmed | P1 | missing | no | yes, needs minute bars / VWAP | none | intraday | yes with minute bars | no | minute_bars missing | no safe substitute | v0.7.3 |
| breakout_confirmed | P2 | missing | no | yes, needs minute bars / levels | none | intraday | yes with minute bars | no | strategy/advice layer not present | diagnostics only later | v0.7.3 |
| breakdown_flag | P2 | missing | no | yes, needs minute bars / levels | none | intraday | yes with minute bars | no | strategy/advice layer not present | diagnostics only later | v0.7.3 |
| intraday_trend | P1 | missing | no | yes, needs minute bars | none | intraday | yes with minute bars | no | minute_bars missing | no safe substitute | v0.7.3 |
| chase_risk | P1 | planned | no | yes, needs position/VWAP/volume | none | intraday | derived | no | advice level layer not present | risk_flags later | v0.7.2 |
| buy_zone | P1 | planned | no | yes, needs rules and base fields | none | intraday | derived | no | not an API field; advice layer not present | allowed_advice_level first | v0.7.2 |
| volume_ratio | P1 | missing | no | yes, needs historical volume/minute bars | none | intraday | derived | no | history baseline missing | use liquidity_flag later | v0.7.3 |
| liquidity_flag | P1 | planned | no | yes, needs volume/amount/spread | none | intraday | derived | future | base liquidity fields missing | amount/volume first | v0.7.1.6 |
| sector_name | P1 | planned | provider_dependent | no | registry/future sector map | static/intraday | not applicable | no | sector registry not built | universe_tags | v0.7.1.6 |
| sector_strength_score | P1 | missing | no | yes, needs universe benchmark | none | intraday | derived | no | scan ranking not built | basic scan count | v0.7.1.6 |
| relative_strength_vs_tech | P1 | missing | no | yes, needs benchmark basket | none | intraday | derived | no | benchmark model missing | compare selected symbols later | v0.7.1.6 |
| relative_strength_vs_hs300 | P1 | missing | no | yes, needs HS300 reference | none | intraday | derived | no | benchmark feed not standardized | 510300 proxy later | v0.7.1.6 |
| sector_leader_flag | P2 | planned | no | yes, needs ranking | none | intraday | derived | no | ranking layer missing | opportunity_rank later | v0.7.1.6 |
| sector_laggard_flag | P2 | planned | no | yes, needs ranking | none | intraday | derived | no | ranking layer missing | opportunity_rank later | v0.7.1.6 |
| iopv | P0 for QDII | missing | provider_dependent | no | none | intraday | provider dependent | no | QDII premium module missing | estimated_nav later | v0.7.4 |
| iopv_time | P0 for QDII | missing | provider_dependent | no | none | intraday | yes if provider supplies | no | QDII premium module missing | quote_time is not IOPV time | v0.7.4 |
| estimated_nav | P0 for QDII | missing | provider_dependent/calculable | yes | none | intraday/daily | provider dependent | no | QDII module missing | IOPV if available | v0.7.4 |
| nav_date | P1 | missing | provider_dependent | no | none | daily | yes | no | QDII module missing | none | v0.7.4 |
| premium_pct | P0 for QDII | missing | no | yes, needs price and NAV/IOPV | none | intraday | derived | no | QDII premium module missing | avoid operation premium judgment | v0.7.4 |
| premium_band | P1 | planned | no | yes, needs premium_pct | none | intraday | derived | no | premium missing | none | v0.7.4 |
| premium_block_flag | P1 | planned | no | yes, needs premium_pct/rules | none | intraday | derived | no | premium missing | none | v0.7.4 |
| fx_rate_usdcny | P0 for QDII | partially_supported | provider_dependent | no | mock controller only | per run | provider dependent | no | real FX not connected | manual/mock reference | v0.7.4 |
| fx_time | P1 | missing | provider_dependent | no | none | provider dependent | yes if FX provider | no | real FX not connected | fetch_time only | v0.7.4 |
| ndx_index_price | P0 for QDII | partially_supported | provider_dependent | no | IXIC mock only | per run | provider dependent | no | no real IXIC/NDX provider | yfinance not connected for IXIC by design | v0.7.4 |
| ndx_index_change_pct | P0 for QDII | missing | provider_dependent | no | none | intraday/US session | provider dependent | no | no real NDX source | QQQ/futures later | v0.7.4 |
| qqq_price | P0 for QDII | missing | provider_dependent | no | none | US session | provider dependent | no | not connected by design | NDX futures later | v0.7.4 |
| qqq_change_pct | P0 for QDII | missing | provider_dependent | yes | none | US session | provider dependent | no | not connected | none | v0.7.4 |
| ndx_futures_price | P0 for QDII | missing | provider_dependent | no | none | futures session | provider dependent | no | no futures provider | NDX/QQQ later | v0.7.4 |
| ndx_futures_change_pct | P0 for QDII | missing | provider_dependent | yes | none | futures session | provider dependent | no | no futures provider | QQQ/NDX if available | v0.7.4 |
| us10y_yield | P2 | missing | provider_dependent | no | none | macro | provider dependent | no | no macro provider | not required current | future |
| dxy | P2 | missing | provider_dependent | no | none | macro/FX | provider dependent | no | no macro provider | not required current | future |
| cnh_rate | P2 | missing | provider_dependent | no | none | FX | provider dependent | no | no CNH provider | USD_CNY mock only | future |
| vix | P2 | missing | provider_dependent | no | none | US session | provider dependent | no | no VIX provider | not required current | future |
| qdii_limit_flag | P2 | planned | no | yes, needs QDII liquidity/subscription info | none | daily/intraday | provider dependent | no | no QDII module | none | v0.7.4 |
| qdii_liquidity_flag | P2 | planned | no | yes, needs amount/volume/spread | none | intraday | derived | no | base fields missing | liquidity_flag later | v0.7.4 |
| stale_iopv_flag | P2 | planned | no | yes, needs iopv_time | none | intraday | derived | no | IOPV missing | stale quote_time is not enough | v0.7.4 |
| gold_cny_manual | P0 | supported | manual | no | manual provider | manual refresh | yes | conditional | manual account price only, not spot gold | manual_prices.yaml | current |
| gold_cny_time | P0 | supported | manual | no | manual provider quote_time | manual refresh | yes | conditional | manual entry risk | data_completeness_report | current |
| cash_available_broker | P2 | missing | broker-only | no | none | account-specific | provider dependent | no | no broker integration | user-provided note later | future |
| cash_pool_total | P2 | missing | account-derived | yes | none | account-specific | provider dependent | no | no position/cash module | out of scope | future |
| gold_position_value | P2 | missing | account-derived | yes | none | account-specific | provider dependent | no | no position valuation | manual price only | future |
| operation_permission / allowed_advice_level | P2 | planned | no | yes | none | per run | derived | no | advice level layer not developed | usable_for_operation now | v0.7.2 |
| action_hint | P2 | planned | no | yes | none | derived | derived | no | not API native; strategy/advice layer only | allowed_advice_level first | v0.7.2 |
| risk_flags | P2 | planned | no | yes | none | derived | derived | no | risk layer not developed | freshness/quality issues now | v0.7.2 |
| opportunity_rank | P2 | planned | no | yes | none | scan-derived | derived | no | scan ranking not developed | scan_universe_report only | v0.7.1.6 |
| preferred_action | P2 | planned | no | yes | none | strategy-derived | derived | no | not API native; not developed | action_hint later | v0.7.2 |

## Module Summary

### Generic Metadata

`symbol`, `name`, `market`, `asset_type`, `selected_provider`, `source`, `fetch_time`, `quote_time`, and `currency` are mostly supported. The main gap is that `market=CN` still combines country-market and exchange semantics.

### Operation / Reference Layer

`quote_purpose`, `quote_trust_tier`, `usable_for_operation`, `usable_for_reference`, `confirmation_required`, strict result, stale flag, provider health, and runtime diagnostics are supported as guard-derived fields.

### A-share ETF Base Quote Fields

`last_price` is supported as `price`. `prev_close`, `open_price`, `high_price`, `low_price`, `volume`, `amount`, and change fields are provider-dependent or partially requested but not standardized into `PriceRecord` / CSV yet.

### Minute Bars / Intraday Fields

minute_bars / VWAP are not developed. Any field depending on minute bars, VWAP, recent volume windows, or intraday confirmation remains missing or planned.

### Intraday Position Derived Fields

Several fields are calculable after base quote normalization and minute bars, but they are not currently supported as operation-grade output.

### Sector And Relative Strength

Sector/ranking fields are planned. `universe_tags` can support future grouping but not relative strength scoring yet.

### QDII Fields

QDII premium is not developed. `iopv`, `estimated_nav`, `premium_pct`, NDX/QQQ/futures, FX, and premium flags are missing or mock-only.

### Gold And Cash Reference

Manual GOLD_CNY is supported as a manually entered account reference. Broker cash and position valuation are not in scope.

### Output Label Fields

`allowed_advice_level`, `action_hint`, `risk_flags`, `opportunity_rank`, and `preferred_action` are planned decision-layer fields, not API-native fields.

## P0 Gap List

- `timezone`: available in parsing/diagnostics but not a stable output column.
- `stale_seconds`: available as `age_seconds` diagnostics but not standardized.
- `data_completeness_level`: expressed through summary/reasons, not a single enum.
- `prev_close`, `open_price`, `high_price`, `low_price`, `volume`, `amount`: standardized in v0.7.1.4 when supplied by provider; still provider-dependent for coverage.
- `bid1_price`, `ask1_price`, `bid1_volume`, `ask1_volume`: missing.
- `minute_bars` or `intraday_vwap` / `intraday_avg_price`: missing.
- QDII `iopv`, `estimated_nav`, `premium_pct`: missing.
- QDII NDX/QQQ/futures reference fields: missing or mock-only.

## P1 Gap List

- `bid_ask_spread`, `turnover_rate`: not standardized. `amplitude_pct`, `price_change`, and `price_change_pct` are standardized/calculable in v0.7.1.4 when required base fields exist.
- Recent volume/amount windows: missing.
- `day_position`, VWAP distance, high/low distance, open gap, intraday return: calculable later, blocked by missing base/minute fields.
- `chase_risk`, `buy_zone`, `volume_ratio`, `liquidity_flag`: planned.
- Sector strength and relative strength: planned.
- QDII `premium_band` and `premium_block_flag`: planned after premium module.

## P2 Gap List

- Sector leader/laggard flags.
- Breakout/breakdown diagnostics.
- Macro/QDII context: US10Y, DXY, CNH, VIX, QDII limit/liquidity flags.
- Broker cash and position valuation.
- `allowed_advice_level`, `action_hint`, `risk_flags`, `opportunity_rank`, `preferred_action`.

## Suggested Roadmap

- v0.7.1.4 Base Quote Field Normalization: standardize `prev_close`, `open_price`, `high_price`, `low_price`, `volume`, `amount`, `price_change`, `price_change_pct`, and exchange/country-market split.
- v0.7.1.5 Provider Capability Expansion: validate provider support for bid/ask, turnover, and stable direct quote fields.
- v0.7.1.6 Scan Universe Basic Ranking: use normalized fields for basic scan status and relative strength placeholders.
- v0.7.2 Advice Level Decision Layer Lite: introduce `allowed_advice_level`, risk flags, and gated output labels without changing provider trust by accident.
- v0.7.3 Minute Bars + VWAP: implement minute bars, VWAP, recent volume windows, and intraday position fields.
- v0.7.4 QDII Premium Module: implement IOPV/NAV/premium, FX, NDX/QQQ/futures references, and QDII-specific stale flags.

## v0.7.1.4 Base Quote Field Normalization Update

v0.7.1.4 standardized base quote fields in the data model, CSV, bundles, and debug reports:

- `last_price`
- `prev_close`
- `open_price`
- `high_price`
- `low_price`
- `volume`
- `amount`
- `price_change`
- `price_change_pct`
- `amplitude_pct`
- `exchange`
- `country_market`
- `trading_calendar`

Current support status for these base quote fields is now `supported` when a selected provider supplies the raw field, and `missing` when that provider does not. `price_change`, `price_change_pct`, and `amplitude_pct` are `calculable` when the required base fields exist. This update does not make any provider operation-grade by itself and does not change strict, freshness, or quote trust tier rules.

`minute_bars / VWAP are not developed`, `QDII premium is not developed`, and `action_hint / preferred_action` remain future strategy or advice-layer fields, not API-native fields.

## v0.7.1.5 Compact Presentation Update

v0.7.1.5 improves presentation and GPT consumption of base quote fields. `0_upload_bundle.md`, project price blocks, candidate watchlist reports, scan reports, and debug bundles now include compact base quote tables or field-source notes.

Provider Capability Notes in v0.7.1.5 are lightweight diagnostic notes only. Formal Provider Capability Expansion / Field Validation is planned for v0.7.1.6. This update does not change provider behavior, provider trust tier, strict, freshness, `minute_bars`, VWAP, or QDII premium status.

## v0.7.1.6 Provider Capability / Field Validation Update

v0.7.1.6 formalizes the provider capability and field validation layer:

- `config/provider_capabilities.yaml` records provider/function field support, units, unit confidence, comparability, `operation_fit`, and `reference_fit`.
- `provider_capability_report.md` is generated for each output directory.
- `prices_snapshot.csv` includes additive field quality columns for unit and comparability diagnostics.
- `volume` and `amount` units are tracked, but they are not normalized unless a provider explicitly has high-confidence unit validation.
- Cross-provider `volume` / `amount` comparison remains unsafe unless `*_comparable_across_providers=true`.
- `bid1_price`, `ask1_price`, and `turnover_rate` remain `not_validated` / `missing` unless a future provider validation proves otherwise.
- `minute_bars`, VWAP, IOPV, and QDII premium remain future modules.

This update does not add providers, does not change provider chain, does not change strict, does not change freshness, and does not upgrade any reference-grade quote to operation-grade.

## v0.7.1.7 Scan Universe Basic Ranking Update

v0.7.1.7 introduces basic scan/watchlist review ranking based on existing base quote and provider capability fields:

- `rankable`
- `watch_priority`
- `scan_score_basic`
- `data_quality_score`
- `momentum_score_basic`
- `field_reliability_score`
- `liquidity_score_basic`
- `reconciliation_score`

This ranking is a data quality and review-priority aid only. It does not implement `minute_bars`, VWAP, QDII premium, `allowed_advice_level`, `action_hint`, or `preferred_action`. It does not change operation/reference semantics or strict.
