# Provider Health Report

行情源健康报告仅用于解释价格事实、接口状态和数据完整度，不提供买卖建议，不做自动交易。

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
- status: not_called

## Manual
- provider: manual
- affected_symbols: GOLD_CNY
- quote_time_status: ok
- usable_for_operation: yes
- symbol=GOLD_CNY, status=success, quote_time=2026-05-18T14:03:00+08:00, source_note=用户手工录入：银行积存金/黄金理财估值价，需以后续实际账户可卖价为准

## Mock
- provider: mock
- function_name=mock_prices.yaml
- status: partial_success
- matched_symbols: 00883.HK, 601899.SH, 601985.SH, 003816.SZ, 159632.SZ, 513300.SH, 159819.SZ, 515880.SH, 510300.SH, USD_CNY, HKD_CNY, IXIC
- affected_symbols: 00883.HK, 601899.SH, 601985.SH, 003816.SZ, 159632.SZ, 513300.SH, 159819.SZ, 515880.SH, 510300.SH, USD_CNY, HKD_CNY, IXIC
- quote_time_status: mixed:ok,stale
- usable_for_operation: yes

## Provider attempts by symbol
### 00883.HK
- provider_priority_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=mock, function_name=mock, status=success, price=21.35, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
### 601899.SH
- provider_priority_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=mock, function_name=mock, status=success, price=18.42, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
### 601985.SH
- provider_priority_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=mock, function_name=mock, status=success, price=10.91, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
### 003816.SZ
- provider_priority_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=mock, function_name=mock, status=success, price=4.27, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
### 159632.SZ
- provider_priority_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=mock, function_name=mock, status=success, price=1.432, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
### 513300.SH
- provider_priority_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=mock, function_name=mock, status=success, price=1.671, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
### 159819.SZ
- provider_priority_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=mock, function_name=mock, status=success, price=0.921, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
### 515880.SH
- provider_priority_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=mock, function_name=mock, status=success, price=1.084, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
### 510300.SH
- provider_priority_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=mock, function_name=mock, status=success, price=3.921, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
### GOLD_CNY
- provider_priority_chain: manual
- selected_provider: manual
- selected_source: manual
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=manual, function_name=manual, status=success, price=1040.0, quote_time=2026-05-18T14:03:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
### USD_CNY
- provider_priority_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: stale
- attempts:
  - provider=mock, function_name=mock, status=success, price=7.215, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
### HKD_CNY
- provider_priority_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: stale
- attempts:
  - provider=mock, function_name=mock, status=success, price=0.925, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
### IXIC
- provider_priority_chain: mock
- selected_provider: mock
- selected_source: mock
- fallback_used: False
- usable_for_operation: True
- selection_reason: selected_provider_returned_usable_price
- final_blocking_reason: 
- attempts:
  - provider=mock, function_name=mock, status=success, price=16835.24, quote_time=2026-05-18T12:45:00+08:00, usable_for_operation=True, reason=, exception_type=, exception_message=
