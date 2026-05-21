# Known Issues

## Market Field For CN Symbols

The default operation paths currently keep A-share and A-share ETF records as `market=CN` in `prices_snapshot.csv`.

Reason: freshness uses the existing `market == "CN"` plus `.SH` / `.SZ` symbol suffix logic to apply the China market trading calendar approximation. Changing `market` directly to `SH` or `SZ` would risk bypassing the current freshness logic.

v0.7.1.4 adds explicit `exchange`, `country_market`, and `trading_calendar` fields (`exchange/country_market/trading_calendar`) while retaining the legacy `market=CN` field to avoid freshness risk. Future cleanup can gradually migrate consumers to the new fields.

Recommended future split:

- `exchange=SH/SZ/HK/US`
- `country_market=CN/HK/US`
- `trading_calendar=CN_A_SHARE/HK/US`

## Eastmoney Direct Stability

Eastmoney Direct remains unstable in the current environment. It is still `reference` / `operation-candidate`, not operation-grade, and it must not pass operation strict by itself.

## Minute Bars And Reference VWAP

Minute bars probe exists, and v0.7.2b adds reference VWAP plus basic intraday position metrics from minute probe artifacts.

The `minute_bars` field remains a probe-derived diagnostic input rather than an operation-grade requirement.

`operation_vwap`, `intraday_vwap`, recent 5m/15m volume windows, and advice-level intraday checks are still not developed. Reference intraday metrics remain diagnostic/reference-only and do not change strict, freshness, quote trust tier, or usable_for_operation.

## QDII Premium

The QDII premium module is not developed. `159632.SZ` and `513300.SH` still lack standardized `iopv`, `estimated_nav`, `premium_pct`, NDX/QQQ/futures, and FX reference fields.

## Scan Universe Base Fields

Scan Universe is currently a basic registry/universe framework. v0.7.1.4 standardizes base quote fields when providers supply them, but candidate quote coverage still depends on existing provider support. Ranking and opportunity scoring remain future work.

## Volume And Amount Units

v0.7.1.6 adds `config/provider_capabilities.yaml`, `provider_capability_report.md`, and CSV field-quality columns to track `volume_unit`, `amount_unit`, unit confidence, and comparability flags.

`volume` and `amount` are still not normalized unless a provider-specific unit has been explicitly validated. Cross-provider volume/amount comparison remains unsafe unless `volume_comparable_across_providers=true` or `amount_comparable_across_providers=true`.

## Bid Ask And Turnover

`bid1_price`, `ask1_price`, related bid/ask volume, and `turnover_rate` remain not validated or missing in v0.7.1.6. The capability layer records this status but does not implement new provider fields.

## Provider Capability And Scan Ranking

Provider Capability Expansion / Field Validation delivered the basic report/config layer in v0.7.1.6. Future scan ranking in v0.7.1.7 should use `field_validation_status`, unit confidence, and comparability flags before using any volume/amount or field-derived ranking input.

## Scan Ranking Limits

v0.7.1.7 adds basic scan/watchlist review ranking. It is intentionally conservative and must not be treated as a trade signal. It does not include sector strength, minute bars, VWAP, QDII premium, bid/ask validation, turnover validation, or advice-level gating. `volume` and `amount` limitations still apply.
## Minute Bars Probe Limits

Minute bars probe introduced in v0.7.2a. It records minute-bar availability and status, but VWAP and intraday derived fields remain not implemented until a later version such as v0.7.2b.

Minute bars availability may vary by provider and symbol. Missing minute bars do not affect operation-grade status, strict, freshness, quote trust tier, or usable_for_operation in v0.7.2a.

The probe does not fix Eastmoney Direct stability, does not add QDII premium, and does not add any advice layer.

## v0.7.2a.1 AKShare Coverage Caveats

AKShare `fund_etf_hist_min_em` may be slow, environment-dependent, or limited to recent ETF minute data. The probe first attempts short interval data and may fall back to a coarser interval when the first response is empty.

YFinance A-share ETF minute bars remain not implemented in guard in this version. Eastmoney Direct minute bars remain not validated.

Some scan symbols may still fail provider coverage and remain not rankable. Such failures should be reported as provider error, symbol not found, empty response, or unsupported coverage rather than treated as a system failure.

## v0.7.2a.2 Eastmoney Minute Probe Caveats

Eastmoney Direct minute probe has been added as a diagnostic fallback after AKShare minute probe failures. The endpoint can still be unstable or provider-dependent, especially around after-close sessions.

Eastmoney Direct minute bars are not operation-grade, do not change strict, and do not calculate VWAP or intraday derived fields.

## v0.7.2a.2a Minute Probe Diagnostics

AKShare minute probe may fail outside CN continuous trading hours, including after the A-share close. The `after_close_possible` flag is diagnostic only and is not a confirmed root cause.

Before declaring AKShare minute bars unusable, rerun `run_tech_minute_probe.ps1` during CN continuous trading hours when practical. This retry suggestion does not change strict, operation readiness, quote trust tier, or usable_for_operation.

## v0.7.2a.2b YFinance Minute Fallback Caveats

YFinance minute bars are attempted only as a reference fallback after AKShare and Eastmoney Direct fail in the optional minute probe path. Intraday ranges are limited, provider-dependent, and not operation-grade.

YFinance fallback success does not change strict, operation readiness, quote trust tier, or usable_for_operation. VWAP and intraday derived fields remain not implemented.

## v0.7.2a.2d Operation Candidate Layer

`tech_operation_candidates` is a reference-only pre-trade verification layer. It is not core holdings and does not make a symbol operation-grade.

A symbol should affect the tech fast strict path only after it is explicitly promoted to `core_holdings`. Operation-candidate provider failures or missing data do not block `run_tech_fast_strict.ps1` or `outputs_tech_latest`.

## v0.7.2b Reference Intraday Metrics Limits

Reference VWAP uses minute-bar close and volume when native amount/volume confidence is not explicit. It is not operation-grade and does not replace QDII premium / IOPV checks.

Spot quotes are used only for alignment diagnostics. Distance to reference VWAP uses the latest minute-bar close, not stale spot last price.
