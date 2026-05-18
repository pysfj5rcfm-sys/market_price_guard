# Provider Health Report

行情源健康报告仅用于解释价格事实、接口状态和数据完整度，不提供买卖建议，不做自动交易。

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
- status: not_called

## Manual
- provider: manual
- affected_symbols: GOLD_CNY
- quote_time_status: ok
- usable_for_operation: yes
- symbol=GOLD_CNY, status=success, quote_time=2026-05-18T14:03:00+08:00, source_note=用户手工录入：银行积存金/黄金理财估值价，需以后续实际账户可卖价为准

## Provider attempts by symbol
### 159632.SZ
- provider_priority_chain: akshare, mock
- selected_provider: akshare
- selected_source: akshare
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=fund_etf_spot_em, status=success, price=2.283, quote_time=2026-05-18T15:34:03+08:00, usable_for_operation=True, elapsed_seconds=29.454, slow_provider_attempt=True, reason=, exception_type=, exception_message=
### 513300.SH
- provider_priority_chain: akshare, mock
- selected_provider: akshare
- selected_source: akshare
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=fund_etf_spot_em, status=success, price=2.5, quote_time=2026-05-18T16:11:53+08:00, usable_for_operation=True, elapsed_seconds=28.727, slow_provider_attempt=True, reason=, exception_type=, exception_message=
### 159819.SZ
- provider_priority_chain: akshare, mock
- selected_provider: akshare
- selected_source: akshare
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=fund_etf_spot_em, status=success, price=1.96, quote_time=2026-05-18T15:34:21+08:00, usable_for_operation=True, elapsed_seconds=28.915, slow_provider_attempt=True, reason=, exception_type=, exception_message=
### 515880.SH
- provider_priority_chain: akshare, mock
- selected_provider: akshare
- selected_source: akshare
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=fund_etf_spot_em, status=success, price=1.517, quote_time=2026-05-18T16:11:34+08:00, usable_for_operation=True, elapsed_seconds=29.448, slow_provider_attempt=True, reason=, exception_type=, exception_message=
### 510300.SH
- provider_priority_chain: akshare, mock
- selected_provider: akshare
- selected_source: akshare
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=akshare, function_name=fund_etf_spot_em, status=success, price=4.852, quote_time=2026-05-18T16:11:48+08:00, usable_for_operation=True, elapsed_seconds=26.432, slow_provider_attempt=True, reason=, exception_type=, exception_message=
### GOLD_CNY
- provider_priority_chain: manual
- selected_provider: manual
- selected_source: manual
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=manual, function_name=manual, status=success, price=1040.0, quote_time=2026-05-18T14:03:00+08:00, usable_for_operation=True, elapsed_seconds=0.003, slow_provider_attempt=False, reason=, exception_type=, exception_message=
