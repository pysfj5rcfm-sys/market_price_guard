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

`volume` and `amount` remain provider raw units unless a provider-specific unit has been explicitly validated. Cross-provider volume/amount comparison remains unsafe until Provider Capability Expansion / Field Validation is completed in a future version such as v0.7.1.6.
