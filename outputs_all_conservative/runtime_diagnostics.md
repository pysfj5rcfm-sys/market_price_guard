# Runtime Diagnostics

- run_start_time_utc: 2026-05-18T11:50:27.639935+00:00
- run_end_time_utc: 2026-05-18T11:54:04.868320+00:00
- total_elapsed_seconds: 217.228
- profile: all
- provider_mode: live
- provider_policy: conservative
- strict: True
- run_time_budget_exceeded: True
- max_run_seconds: 30.0
- max_data_lag_seconds: 300.0
- max_quote_lag_seconds: 25744.868
- oldest_quote_time: 2026-05-18T12:45:00+08:00
- newest_quote_time: 2026-05-18T16:11:53+08:00

## per_provider_elapsed_seconds
- akshare: 302.259
- yfinance: 3.678
- mock: 0.033
- manual: 0.003

## per_symbol_elapsed_seconds
- 00883.HK: 69.764
- 601899.SH: 30.199
- 601985.SH: 27.955
- 003816.SZ: 30.762
- 159632.SZ: 29.721
- 513300.SH: 31.49
- 159819.SZ: 30.152
- 515880.SH: 30.873
- 510300.SH: 25.021
- GOLD_CNY: 0.003
- USD_CNY: 0.012
- HKD_CNY: 0.01
- IXIC: 0.011

## slow_provider_attempts
- symbol=00883.HK, provider=akshare, function_name=stock_hk_spot_em, elapsed_seconds=22.53, timeout_seconds=8.0, reason=provider_timeout
- symbol=00883.HK, provider=akshare, function_name=stock_hk_main_board_spot_em, elapsed_seconds=22.53, timeout_seconds=8.0, reason=provider_timeout
- symbol=00883.HK, provider=akshare, function_name=stock_hsgt_sh_hk_spot_em, elapsed_seconds=22.53, timeout_seconds=8.0, reason=provider_timeout
- symbol=601899.SH, provider=akshare, function_name=stock_zh_a_spot_em, elapsed_seconds=14.822, timeout_seconds=8.0, reason=provider_timeout
- symbol=601899.SH, provider=akshare, function_name=stock_sh_a_spot_em, elapsed_seconds=14.822, timeout_seconds=8.0, reason=provider_timeout
- symbol=601985.SH, provider=akshare, function_name=stock_zh_a_spot_em, elapsed_seconds=13.719, timeout_seconds=8.0, reason=provider_timeout
- symbol=601985.SH, provider=akshare, function_name=stock_sh_a_spot_em, elapsed_seconds=13.719, timeout_seconds=8.0, reason=provider_timeout
- symbol=003816.SZ, provider=akshare, function_name=stock_zh_a_spot_em, elapsed_seconds=15.165, timeout_seconds=8.0, reason=provider_timeout
- symbol=003816.SZ, provider=akshare, function_name=stock_sz_a_spot_em, elapsed_seconds=15.165, timeout_seconds=8.0, reason=provider_timeout
- symbol=159632.SZ, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=29.721, timeout_seconds=8.0, reason=
- symbol=513300.SH, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=31.49, timeout_seconds=8.0, reason=
- symbol=159819.SZ, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=30.152, timeout_seconds=8.0, reason=
- symbol=515880.SH, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=30.873, timeout_seconds=8.0, reason=
- symbol=510300.SH, provider=akshare, function_name=fund_etf_spot_em, elapsed_seconds=25.021, timeout_seconds=8.0, reason=
