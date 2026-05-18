# Provider Health Report

行情源健康报告仅用于解释价格事实、接口状态和数据完整度，不提供买卖建议，不做自动交易。

- provider_policy=diagnostic
- diagnostic mode active: provider diagnostics may run slower than fast mode.

## AKShare ETF
- provider: akshare
- market_category: ETF
- affected_symbols: 159632.SZ, 513300.SH, 159819.SZ, 515880.SH, 510300.SH
- quote_time_status: ok
- usable_for_operation: yes
- function_name=fund_etf_spot_em, status=success, returned_rows=1467, matched_symbols=159632.SZ, 513300.SH, 159819.SZ, 515880.SH, 510300.SH, affected_symbols=159632.SZ, 513300.SH, 159819.SZ, 515880.SH, 510300.SH, exception_type=, exception_message=

## AKShare A股
- provider: akshare
- market_category: A_SHARE
- affected_symbols: 601899.SH, 601985.SH, 003816.SZ
- quote_time_status: ok
- usable_for_operation: yes
- function_name=stock_zh_a_spot_em, status=failed, returned_rows=, matched_symbols=, affected_symbols=601899.SH, 601985.SH, 003816.SZ, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- function_name=stock_sh_a_spot_em, status=failed, returned_rows=, matched_symbols=, affected_symbols=601899.SH, 601985.SH, 003816.SZ, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- function_name=stock_sz_a_spot_em, status=failed, returned_rows=, matched_symbols=, affected_symbols=601899.SH, 601985.SH, 003816.SZ, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

## AKShare 港股
- provider: akshare
- market_category: HK
- affected_symbols: 00883.HK
- quote_time_status: ok
- usable_for_operation: yes
- function_name=stock_hk_spot_em, status=failed, returned_rows=, matched_symbols=, affected_symbols=00883.HK, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- function_name=stock_hk_main_board_spot_em, status=failed, returned_rows=, matched_symbols=, affected_symbols=00883.HK, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- function_name=stock_hsgt_sh_hk_spot_em, status=failed, returned_rows=, matched_symbols=, affected_symbols=00883.HK, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

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
- affected_symbols: GOLD_CNY
- quote_time_status: ok
- usable_for_operation: yes
- symbol=GOLD_CNY, status=success, quote_time=2026-05-18T14:03:00+08:00, source_note=用户手工录入：银行积存金/黄金理财估值价，需以后续实际账户可卖价为准

## Provider attempts by symbol
### 00883.HK
- provider_policy: diagnostic
- configured_provider_priority: akshare, yfinance, mock
- effective_provider_chain: akshare, yfinance, mock
- selected_provider: yfinance
- selected_source: yfinance
- fallback_used: True
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=stock_hk_spot_em, status=failed, price=, quote_time=, usable_for_operation=False, elapsed_seconds=23.37, slow_provider_attempt=True, reason=provider_timeout, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
  - provider=akshare, function_name=stock_hk_main_board_spot_em, status=failed, price=, quote_time=, usable_for_operation=False, elapsed_seconds=23.37, slow_provider_attempt=True, reason=provider_timeout, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
  - provider=akshare, function_name=stock_hsgt_sh_hk_spot_em, status=failed, price=, quote_time=, usable_for_operation=False, elapsed_seconds=23.37, slow_provider_attempt=True, reason=provider_timeout, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
  - provider=yfinance, function_name=yfinance.Ticker, status=success, price=26.760000228881836, quote_time=2026-05-18T16:08:00+08:00, usable_for_operation=True, elapsed_seconds=2.805, slow_provider_attempt=False, reason=, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:diagnostic, exception_type=, exception_message=
### 601899.SH
- provider_policy: diagnostic
- configured_provider_priority: akshare, yfinance, mock
- effective_provider_chain: akshare, yfinance, mock
- selected_provider: yfinance
- selected_source: yfinance
- fallback_used: True
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=stock_zh_a_spot_em, status=failed, price=, quote_time=, usable_for_operation=False, elapsed_seconds=14.397, slow_provider_attempt=True, reason=provider_timeout, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
  - provider=akshare, function_name=stock_sh_a_spot_em, status=failed, price=, quote_time=, usable_for_operation=False, elapsed_seconds=14.397, slow_provider_attempt=True, reason=provider_timeout, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
  - provider=yfinance, function_name=yfinance.Ticker, status=success, price=31.299999237060547, quote_time=2026-05-18T14:57:00+08:00, usable_for_operation=True, elapsed_seconds=0.929, slow_provider_attempt=False, reason=, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:diagnostic, exception_type=, exception_message=
### 601985.SH
- provider_policy: diagnostic
- configured_provider_priority: akshare, yfinance, mock
- effective_provider_chain: akshare, yfinance, mock
- selected_provider: yfinance
- selected_source: yfinance
- fallback_used: True
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=stock_zh_a_spot_em, status=failed, price=, quote_time=, usable_for_operation=False, elapsed_seconds=14.738, slow_provider_attempt=True, reason=provider_timeout, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
  - provider=akshare, function_name=stock_sh_a_spot_em, status=failed, price=, quote_time=, usable_for_operation=False, elapsed_seconds=14.738, slow_provider_attempt=True, reason=provider_timeout, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
  - provider=yfinance, function_name=yfinance.Ticker, status=success, price=9.050000190734863, quote_time=2026-05-18T14:56:00+08:00, usable_for_operation=True, elapsed_seconds=0.765, slow_provider_attempt=False, reason=, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:diagnostic, exception_type=, exception_message=
### 003816.SZ
- provider_policy: diagnostic
- configured_provider_priority: akshare, yfinance, mock
- effective_provider_chain: akshare, yfinance, mock
- selected_provider: yfinance
- selected_source: yfinance
- fallback_used: True
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=stock_zh_a_spot_em, status=failed, price=, quote_time=, usable_for_operation=False, elapsed_seconds=14.662, slow_provider_attempt=True, reason=provider_timeout, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
  - provider=akshare, function_name=stock_sz_a_spot_em, status=failed, price=, quote_time=, usable_for_operation=False, elapsed_seconds=14.662, slow_provider_attempt=True, reason=provider_timeout, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
  - provider=yfinance, function_name=yfinance.Ticker, status=success, price=4.800000190734863, quote_time=2026-05-18T14:59:00+08:00, usable_for_operation=True, elapsed_seconds=0.792, slow_provider_attempt=False, reason=, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:diagnostic, exception_type=, exception_message=
### 159632.SZ
- provider_policy: diagnostic
- configured_provider_priority: akshare, mock
- effective_provider_chain: akshare, mock
- selected_provider: akshare
- selected_source: akshare
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=fund_etf_spot_em, status=success, price=2.283, quote_time=2026-05-18T15:34:03+08:00, usable_for_operation=True, elapsed_seconds=25.64, slow_provider_attempt=True, reason=, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:diagnostic, exception_type=, exception_message=
### 513300.SH
- provider_policy: diagnostic
- configured_provider_priority: akshare, mock
- effective_provider_chain: akshare, mock
- selected_provider: akshare
- selected_source: akshare
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=fund_etf_spot_em, status=success, price=2.5, quote_time=2026-05-18T16:11:53+08:00, usable_for_operation=True, elapsed_seconds=27.044, slow_provider_attempt=True, reason=, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:diagnostic, exception_type=, exception_message=
### 159819.SZ
- provider_policy: diagnostic
- configured_provider_priority: akshare, mock
- effective_provider_chain: akshare, mock
- selected_provider: akshare
- selected_source: akshare
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=fund_etf_spot_em, status=success, price=1.96, quote_time=2026-05-18T15:34:21+08:00, usable_for_operation=True, elapsed_seconds=30.016, slow_provider_attempt=True, reason=, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:diagnostic, exception_type=, exception_message=
### 515880.SH
- provider_policy: diagnostic
- configured_provider_priority: akshare, mock
- effective_provider_chain: akshare, mock
- selected_provider: akshare
- selected_source: akshare
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=fund_etf_spot_em, status=success, price=1.517, quote_time=2026-05-18T16:11:34+08:00, usable_for_operation=True, elapsed_seconds=28.127, slow_provider_attempt=True, reason=, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:diagnostic, exception_type=, exception_message=
### 510300.SH
- provider_policy: diagnostic
- configured_provider_priority: akshare, mock
- effective_provider_chain: akshare, mock
- selected_provider: akshare
- selected_source: akshare
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=fund_etf_spot_em, status=success, price=4.852, quote_time=2026-05-18T16:11:48+08:00, usable_for_operation=True, elapsed_seconds=30.547, slow_provider_attempt=True, reason=, exception_type=, exception_message=
  - provider=mock, function_name=mock, status=skipped, price=, quote_time=, usable_for_operation=False, elapsed_seconds=0.0, slow_provider_attempt=False, reason=selected_provider_success_policy_skip:diagnostic, exception_type=, exception_message=
### GOLD_CNY
- provider_policy: diagnostic
- configured_provider_priority: manual
- effective_provider_chain: manual
- selected_provider: manual
- selected_source: manual
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=manual, function_name=manual, status=success, price=1040.0, quote_time=2026-05-18T14:03:00+08:00, usable_for_operation=True, elapsed_seconds=0.006, slow_provider_attempt=False, reason=, exception_type=, exception_message=
### USD_CNY
- provider_policy: diagnostic
- configured_provider_priority: mock
- effective_provider_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: stale
- attempts:
  - provider=mock, function_name=mock, status=success, price=7.215, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, elapsed_seconds=0.017, slow_provider_attempt=False, reason=, exception_type=, exception_message=
### HKD_CNY
- provider_policy: diagnostic
- configured_provider_priority: mock
- effective_provider_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: stale
- attempts:
  - provider=mock, function_name=mock, status=success, price=0.925, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, elapsed_seconds=0.017, slow_provider_attempt=False, reason=, exception_type=, exception_message=
### IXIC
- provider_policy: diagnostic
- configured_provider_priority: mock
- effective_provider_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=mock, function_name=mock, status=success, price=16835.24, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, elapsed_seconds=0.018, slow_provider_attempt=False, reason=, exception_type=, exception_message=
