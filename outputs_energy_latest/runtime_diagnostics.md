# Runtime Diagnostics

- run_start_time_utc: 2026-05-18T11:25:43.348657+00:00
- run_end_time_utc: 2026-05-18T11:26:58.751835+00:00
- total_elapsed_seconds: 75.403
- profile: energy
- provider_mode: live
- strict: True
- run_time_budget_exceeded: True
- max_run_seconds: 30.0
- max_data_lag_seconds: 300.0
- max_quote_lag_seconds: 16258.752
- oldest_quote_time: 2026-05-18T14:56:00+08:00
- newest_quote_time: 2026-05-18T16:08:00+08:00

## per_provider_elapsed_seconds
- akshare: 165.033
- yfinance: 4.916

## per_symbol_elapsed_seconds
- 00883.HK: 75.018
- 601899.SH: 31.399
- 601985.SH: 31.998
- 003816.SZ: 31.534

## slow_provider_attempts
- symbol=00883.HK, provider=akshare, function_name=stock_hk_spot_em, elapsed_seconds=24.105, timeout_seconds=8.0, reason=provider_timeout
- symbol=00883.HK, provider=akshare, function_name=stock_hk_main_board_spot_em, elapsed_seconds=24.105, timeout_seconds=8.0, reason=provider_timeout
- symbol=00883.HK, provider=akshare, function_name=stock_hsgt_sh_hk_spot_em, elapsed_seconds=24.105, timeout_seconds=8.0, reason=provider_timeout
- symbol=601899.SH, provider=akshare, function_name=stock_zh_a_spot_em, elapsed_seconds=15.318, timeout_seconds=8.0, reason=provider_timeout
- symbol=601899.SH, provider=akshare, function_name=stock_sh_a_spot_em, elapsed_seconds=15.318, timeout_seconds=8.0, reason=provider_timeout
- symbol=601985.SH, provider=akshare, function_name=stock_zh_a_spot_em, elapsed_seconds=15.62, timeout_seconds=8.0, reason=provider_timeout
- symbol=601985.SH, provider=akshare, function_name=stock_sh_a_spot_em, elapsed_seconds=15.62, timeout_seconds=8.0, reason=provider_timeout
- symbol=003816.SZ, provider=akshare, function_name=stock_zh_a_spot_em, elapsed_seconds=15.421, timeout_seconds=8.0, reason=provider_timeout
- symbol=003816.SZ, provider=akshare, function_name=stock_sz_a_spot_em, elapsed_seconds=15.421, timeout_seconds=8.0, reason=provider_timeout
