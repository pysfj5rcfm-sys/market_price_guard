# Known Issues

## Market Field For CN Symbols

The default operation paths currently keep A-share and A-share ETF records as `market=CN` in `prices_snapshot.csv`.

Reason: freshness uses the existing `market == "CN"` plus `.SH` / `.SZ` symbol suffix logic to apply the China market trading calendar approximation. Changing `market` directly to `SH` or `SZ` would risk bypassing the current freshness logic.

Future cleanup should add an explicit exchange-level field, for example `exchange=SH/SZ` or `country_market=CN`, then migrate reports without changing freshness semantics.
