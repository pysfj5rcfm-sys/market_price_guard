# Runtime Diagnostics

- run_start_time_utc: 2026-05-18T11:47:51.808873+00:00
- run_end_time_utc: 2026-05-18T11:50:09.225536+00:00
- total_elapsed_seconds: 137.417
- profile: tech
- provider_mode: live
- provider_policy: fast
- strict: True
- run_time_budget_exceeded: True
- max_run_seconds: 30.0
- max_data_lag_seconds: 300.0
- max_quote_lag_seconds: 20829.226
- oldest_quote_time: 2026-05-18T14:03:00+08:00
- newest_quote_time: 2026-05-18T16:11:53+08:00

## per_provider_elapsed_seconds
- akshare: 137.391
- mock: 0.0
- manual: 0.004

## per_symbol_elapsed_seconds
- 159632.SZ: 27.944
- 513300.SH: 27.551
- 159819.SZ: 26.909
- 515880.SH: 26.549
- 510300.SH: 28.438
- GOLD_CNY: 0.004

## slow_provider_attempts
- symbol=159632.SZ, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=27.944, timeout_seconds=8.0, reason=
- symbol=513300.SH, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=27.551, timeout_seconds=8.0, reason=
- symbol=159819.SZ, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=26.909, timeout_seconds=8.0, reason=
- symbol=515880.SH, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=26.549, timeout_seconds=8.0, reason=
- symbol=510300.SH, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=28.438, timeout_seconds=8.0, reason=
