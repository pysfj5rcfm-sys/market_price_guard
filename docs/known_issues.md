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

## Minute Bars And VWAP

`minute_bars`, `intraday_vwap`, recent 5m/15m volume windows, and VWAP-derived intraday position fields are not developed yet. Intraday position and chase-risk diagnostics remain insufficient until a minute-bar module exists.

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
