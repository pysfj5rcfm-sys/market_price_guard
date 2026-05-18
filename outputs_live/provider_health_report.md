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
- affected_symbols: 601899.SH, 601985.SH, 003816.SZ
- quote_time_status: missing
- usable_for_operation: no
- function_name=stock_zh_a_spot_em, status=failed, returned_rows=, matched_symbols=, affected_symbols=601899.SH, 601985.SH, 003816.SZ, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- function_name=stock_sh_a_spot_em, status=failed, returned_rows=, matched_symbols=, affected_symbols=601899.SH, 601985.SH, 003816.SZ, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- function_name=stock_sz_a_spot_em, status=failed, returned_rows=, matched_symbols=, affected_symbols=601899.SH, 601985.SH, 003816.SZ, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

## AKShare 港股
- provider: akshare
- market_category: HK
- affected_symbols: 00883.HK
- quote_time_status: missing
- usable_for_operation: no
- function_name=stock_hk_spot_em, status=failed, returned_rows=, matched_symbols=, affected_symbols=00883.HK, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- function_name=stock_hk_main_board_spot_em, status=failed, returned_rows=, matched_symbols=, affected_symbols=00883.HK, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- function_name=stock_hsgt_sh_hk_spot_em, status=failed, returned_rows=, matched_symbols=, affected_symbols=00883.HK, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

## Manual
- provider: manual
- affected_symbols: GOLD_CNY
- quote_time_status: ok
- usable_for_operation: yes
- symbol=GOLD_CNY, status=success, quote_time=2026-05-18T14:03:00+08:00, source_note=用户手工录入：银行积存金/黄金理财估值价，需以后续实际账户可卖价为准
