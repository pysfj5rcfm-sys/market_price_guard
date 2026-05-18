# 数据完整度报告

可用于具体操作建议：否

本工具不做自动交易，不输出买卖建议，只输出价格事实、数据源、时间戳、市场状态和数据完整度。

## Strict blocking records
- project=energy, symbol=00883.HK, name=中海油H, source=akshare, quote_time=, is_stale=True, stale_reason=provider_error: 行情源调用失败，不可用于具体操作建议；provider_error, blocking_reason=provider_error, function_name=stock_hk_spot_em, exception_type=ConnectionError
- project=energy, symbol=601899.SH, name=紫金矿业A, source=akshare, quote_time=, is_stale=True, stale_reason=provider_error: 行情源调用失败，不可用于具体操作建议；provider_error, blocking_reason=provider_error, function_name=stock_zh_a_spot_em, exception_type=ConnectionError
- project=energy, symbol=601985.SH, name=中国核电, source=akshare, quote_time=, is_stale=True, stale_reason=provider_error: 行情源调用失败，不可用于具体操作建议；provider_error, blocking_reason=provider_error, function_name=stock_zh_a_spot_em, exception_type=ConnectionError
- project=energy, symbol=003816.SZ, name=中国广核, source=akshare, quote_time=, is_stale=True, stale_reason=provider_error: 行情源调用失败，不可用于具体操作建议；provider_error, blocking_reason=provider_error, function_name=stock_zh_a_spot_em, exception_type=ConnectionError
- project=tech, symbol=159632.SZ, name=纳斯达克ETF华安, source=akshare, quote_time=, is_stale=True, stale_reason=quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing, blocking_reason=quote_time_missing, function_name=fund_etf_spot_em, exception_type=
- project=tech, symbol=513300.SH, name=纳斯达克ETF华夏, source=akshare, quote_time=, is_stale=True, stale_reason=quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing, blocking_reason=quote_time_missing, function_name=fund_etf_spot_em, exception_type=
- project=tech, symbol=159819.SZ, name=人工智能ETF易方达, source=akshare, quote_time=, is_stale=True, stale_reason=quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing, blocking_reason=quote_time_missing, function_name=fund_etf_spot_em, exception_type=
- project=tech, symbol=515880.SH, name=通信ETF国泰, source=akshare, quote_time=, is_stale=True, stale_reason=quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing, blocking_reason=quote_time_missing, function_name=fund_etf_spot_em, exception_type=

## Provider diagnostics
- AKShare partially succeeded
- stock_zh_a_spot_em: fail, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- stock_hk_spot_em: fail, exception_type=ConnectionError, exception_message=('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- fund_etf_spot_em: success, returned_rows=1467, matched_symbols=['159632.SZ', '513300.SH', '159819.SZ', '515880.SH', '510300.SH']

## AKShare price records
- energy 00883.HK 中海油H: provider_error: 行情源调用失败，不可用于具体操作建议；provider_error
- energy 601899.SH 紫金矿业A: provider_error: 行情源调用失败，不可用于具体操作建议；provider_error
- energy 601985.SH 中国核电: provider_error: 行情源调用失败，不可用于具体操作建议；provider_error
- energy 003816.SZ 中国广核: provider_error: 行情源调用失败，不可用于具体操作建议；provider_error
- tech 159632.SZ 纳斯达克ETF华安: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- tech 513300.SH 纳斯达克ETF华夏: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- tech 159819.SZ 人工智能ETF易方达: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- tech 515880.SH 通信ETF国泰: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- tech 510300.SH 沪深300ETF华泰柏瑞: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing

## AKShare / 数据质量问题
- energy 00883.HK 中海油H: provider_error
- energy 601899.SH 紫金矿业A: provider_error
- energy 601985.SH 中国核电: provider_error
- energy 003816.SZ 中国广核: provider_error
- tech 159632.SZ 纳斯达克ETF华安: quote_time_missing
- tech 513300.SH 纳斯达克ETF华夏: quote_time_missing
- tech 159819.SZ 人工智能ETF易方达: quote_time_missing
- tech 515880.SH 通信ETF国泰: quote_time_missing
- tech 510300.SH 沪深300ETF华泰柏瑞: quote_time_missing

## 黄金手工价说明
黄金持仓参考价为用户手工录入价，不等同于国际现货金价；用于科技账户防守仓/潜在转科技资金的参考，实际操作前需核对账户内可卖价、手续费、点差和到账规则。

## 如果为否，原因
- 存在价格缺失
- 存在 stale 价格
- 存在 quote_time_missing，无法证明价格新鲜

## 缺失价格列表
- energy 00883.HK 中海油H: provider_error: 行情源调用失败，不可用于具体操作建议；provider_error
- energy 601899.SH 紫金矿业A: provider_error: 行情源调用失败，不可用于具体操作建议；provider_error
- energy 601985.SH 中国核电: provider_error: 行情源调用失败，不可用于具体操作建议；provider_error
- energy 003816.SZ 中国广核: provider_error: 行情源调用失败，不可用于具体操作建议；provider_error

## stale 价格列表
- tech 159632.SZ 纳斯达克ETF华安: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- tech 513300.SH 纳斯达克ETF华夏: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- tech 159819.SZ 人工智能ETF易方达: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- tech 515880.SH 通信ETF国泰: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- tech 510300.SH 沪深300ETF华泰柏瑞: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- controller USD_CNY 美元兑人民币: 交易中价格超过 max_age_seconds，不可用于具体操作建议
- controller HKD_CNY 港币兑人民币: 交易中价格超过 max_age_seconds，不可用于具体操作建议

## quote_time 缺失列表
- quote_time_missing: energy 00883.HK 中海油H: provider_error: 行情源调用失败，不可用于具体操作建议；provider_error
- quote_time_missing: energy 601899.SH 紫金矿业A: provider_error: 行情源调用失败，不可用于具体操作建议；provider_error
- quote_time_missing: energy 601985.SH 中国核电: provider_error: 行情源调用失败，不可用于具体操作建议；provider_error
- quote_time_missing: energy 003816.SZ 中国广核: provider_error: 行情源调用失败，不可用于具体操作建议；provider_error
- quote_time_missing: tech 159632.SZ 纳斯达克ETF华安: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- quote_time_missing: tech 513300.SH 纳斯达克ETF华夏: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- quote_time_missing: tech 159819.SZ 人工智能ETF易方达: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- quote_time_missing: tech 515880.SH 通信ETF国泰: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- quote_time_missing: tech 510300.SH 沪深300ETF华泰柏瑞: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing

## manual price records
- GOLD_CNY 黄金持仓参考价: price=1040.0, quote_time=2026-05-18T14:03:00+08:00, is_stale=False, source_note=用户手工录入：银行积存金/黄金理财估值价，需以后续实际账户可卖价为准, fee_note=手续费、点差、赎回到账规则未自动计算, asset_role=defense_or_potential_tech_funding

## warning
- tech 510300.SH 沪深300ETF华泰柏瑞: quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；quote_time_missing
- controller USD_CNY 美元兑人民币: 交易中价格超过 max_age_seconds，不可用于具体操作建议
- controller HKD_CNY 港币兑人民币: 交易中价格超过 max_age_seconds，不可用于具体操作建议

## 不确定性
- 手续费、点差、赎回到账规则未自动计算。
- GOLD_CNY 需以后续实际账户可卖价为准。

## 允许使用范围
- 可用于价格事实同步、数据源核对、时间戳核对、市场状态核对和数据完整度检查。
- 收盘后价格仅可作为收盘/最后成交参考。
- GOLD_CNY 仅可作为科技账户防守仓/潜在转科技资金参考。

## 禁止使用范围
- 不可用于自动交易。
- 不输出买卖建议。
- 若 required_for_operation 指标缺失、stale、quote_time 缺失或无效，不可用于具体操作建议。
- 收盘/最后成交参考价不可用于盘中做T。
