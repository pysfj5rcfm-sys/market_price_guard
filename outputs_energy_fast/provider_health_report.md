# Provider Health Report

行情源健康报告仅用于解释价格事实、接口状态和数据完整度，不提供买卖建议，不做自动交易。

- provider_policy=fast

## AKShare ETF
- provider: akshare
- market_category: ETF
- affected_symbols: 
- quote_time_status: not_available
- usable_for_operation: no
- status: not_called
- function_name=fund_etf_spot_em, status=not_called

## AKShare A股
- provider: akshare
- market_category: A_SHARE
- affected_symbols: 
- quote_time_status: not_available
- usable_for_operation: no
- status: not_called
- function_name=stock_zh_a_spot_em, status=not_called
- function_name=stock_sh_a_spot_em, status=not_called
- function_name=stock_sz_a_spot_em, status=not_called

## AKShare 港股
- provider: akshare
- market_category: HK
- affected_symbols: 
- quote_time_status: not_available
- usable_for_operation: no
- status: not_called
- function_name=stock_hk_spot_em, status=not_called
- function_name=stock_hk_main_board_spot_em, status=not_called
- function_name=stock_hsgt_sh_hk_spot_em, status=not_called

## YFinance 港股 / A股
- provider: yfinance
- market_category: HK/A_SHARE
- affected_symbols: 00883.HK, 601899.SH, 601985.SH, 003816.SZ
- quote_time_status: ok
- usable_for_operation: yes
- source_limit_note: yfinance is an open-source Yahoo Finance public API wrapper for research/educational use; not an official exchange feed
- function_name=yfinance.Ticker, status=success, returned_rows=, matched_symbols=00883.HK, affected_symbols=00883.HK, exception_type=, exception_message=
- function_name=yfinance.Ticker, status=success, returned_rows=, matched_symbols=601899.SH, affected_symbols=601899.SH, exception_type=, exception_message=
- function_name=yfinance.Ticker, status=success, returned_rows=, matched_symbols=601985.SH, affected_symbols=601985.SH, exception_type=, exception_message=
- function_name=yfinance.Ticker, status=success, returned_rows=, matched_symbols=003816.SZ, affected_symbols=003816.SZ, exception_type=, exception_message=

## Manual
- provider: manual
- status: not_called

## Provider attempts by symbol
### 00883.HK
- provider_policy: fast
- configured_provider_priority: akshare, yfinance, mock
- effective_provider_chain: yfinance, akshare, mock
- selected_provider: yfinance
- selected_source: yfinance
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=yfinance, function_name=yfinance.Ticker, status=success, price=26.760000228881836, quote_time=2026-05-18T16:08:00+08:00, usable_for_operation=True, elapsed_seconds=3.246, slow_provider_attempt=False, reason=, exception_type=, exception_message=
  - provider=akshare, function_name=akshare, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:fast, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:fast, exception_type=, exception_message=
### 601899.SH
- provider_policy: fast
- configured_provider_priority: akshare, yfinance, mock
- effective_provider_chain: yfinance, akshare, mock
- selected_provider: yfinance
- selected_source: yfinance
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=yfinance, function_name=yfinance.Ticker, status=success, price=31.299999237060547, quote_time=2026-05-18T14:57:00+08:00, usable_for_operation=True, elapsed_seconds=0.764, slow_provider_attempt=False, reason=, exception_type=, exception_message=
  - provider=akshare, function_name=akshare, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:fast, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:fast, exception_type=, exception_message=
### 601985.SH
- provider_policy: fast
- configured_provider_priority: akshare, yfinance, mock
- effective_provider_chain: yfinance, akshare, mock
- selected_provider: yfinance
- selected_source: yfinance
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=yfinance, function_name=yfinance.Ticker, status=success, price=9.050000190734863, quote_time=2026-05-18T14:56:00+08:00, usable_for_operation=True, elapsed_seconds=0.779, slow_provider_attempt=False, reason=, exception_type=, exception_message=
  - provider=akshare, function_name=akshare, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:fast, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:fast, exception_type=, exception_message=
### 003816.SZ
- provider_policy: fast
- configured_provider_priority: akshare, yfinance, mock
- effective_provider_chain: yfinance, akshare, mock
- selected_provider: yfinance
- selected_source: yfinance
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=yfinance, function_name=yfinance.Ticker, status=success, price=4.800000190734863, quote_time=2026-05-18T14:59:00+08:00, usable_for_operation=True, elapsed_seconds=0.754, slow_provider_attempt=False, reason=, exception_type=, exception_message=
  - provider=akshare, function_name=akshare, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:fast, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:fast, exception_type=, exception_message=
