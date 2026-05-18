# Runtime Diagnostics

- run_start_time_utc: 2026-05-18T11:56:04.198458+00:00
- run_end_time_utc: 2026-05-18T11:59:38.114001+00:00
- total_elapsed_seconds: 213.916
- profile: all
- provider_mode: live
- provider_policy: diagnostic
- strict: False
- run_time_budget_exceeded: True
- max_run_seconds: 30.0
- max_data_lag_seconds: 300.0
- max_quote_lag_seconds: 26078.114
- oldest_quote_time: 2026-05-18T12:45:00+08:00
- newest_quote_time: 2026-05-18T16:11:53+08:00

## per_provider_elapsed_seconds
- akshare: 299.078
- yfinance: 5.291
- mock: 0.052
- manual: 0.006

## per_symbol_elapsed_seconds
- 00883.HK: 72.915
- 601899.SH: 29.723
- 601985.SH: 30.241
- 003816.SZ: 30.116
- 159632.SZ: 25.64
- 513300.SH: 27.044
- 159819.SZ: 30.016
- 515880.SH: 28.127
- 510300.SH: 30.547
- GOLD_CNY: 0.006
- USD_CNY: 0.017
- HKD_CNY: 0.017
- IXIC: 0.018

## slow_provider_attempts
- symbol=00883.HK, provider=akshare, function_name=stock_hk_spot_em, elapsed_seconds=23.37, timeout_seconds=8.0, reason=provider_timeout
- symbol=00883.HK, provider=akshare, function_name=stock_hk_main_board_spot_em, elapsed_seconds=23.37, timeout_seconds=8.0, reason=provider_timeout
- symbol=00883.HK, provider=akshare, function_name=stock_hsgt_sh_hk_spot_em, elapsed_seconds=23.37, timeout_seconds=8.0, reason=provider_timeout
- symbol=601899.SH, provider=akshare, function_name=stock_zh_a_spot_em, elapsed_seconds=14.397, timeout_seconds=8.0, reason=provider_timeout
- symbol=601899.SH, provider=akshare, function_name=stock_sh_a_spot_em, elapsed_seconds=14.397, timeout_seconds=8.0, reason=provider_timeout
- symbol=601985.SH, provider=akshare, function_name=stock_zh_a_spot_em, elapsed_seconds=14.738, timeout_seconds=8.0, reason=provider_timeout
- symbol=601985.SH, provider=akshare, function_name=stock_sh_a_spot_em, elapsed_seconds=14.738, timeout_seconds=8.0, reason=provider_timeout
- symbol=003816.SZ, provider=akshare, function_name=stock_zh_a_spot_em, elapsed_seconds=14.662, timeout_seconds=8.0, reason=provider_timeout
- symbol=003816.SZ, provider=akshare, function_name=stock_sz_a_spot_em, elapsed_seconds=14.662, timeout_seconds=8.0, reason=provider_timeout
- symbol=159632.SZ, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=25.64, timeout_seconds=8.0, reason=
- symbol=513300.SH, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=27.044, timeout_seconds=8.0, reason=
- symbol=159819.SZ, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=30.016, timeout_seconds=8.0, reason=
- symbol=515880.SH, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=28.127, timeout_seconds=8.0, reason=
- symbol=510300.SH, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=30.547, timeout_seconds=8.0, reason=

## provider_policy_note
- diagnostic mode active: may run slower than fast mode.
