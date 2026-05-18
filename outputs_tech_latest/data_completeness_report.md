# 数据完整度报告

可用于具体操作建议：是

本工具不做自动交易，不输出买卖建议，只输出价格事实、数据源、时间戳、市场状态和数据完整度。

行情源健康状态详见 provider_health_report.md。

## Strict blocking records
- 无

## Provider diagnostics
- stock_zh_a_spot_em: not_called
- stock_sh_a_spot_em: not_called
- stock_sz_a_spot_em: not_called
- stock_hk_spot_em: not_called
- stock_hk_main_board_spot_em: not_called
- stock_hsgt_sh_hk_spot_em: not_called
- fund_etf_spot_em: success, provider_status=success, returned_rows=1467, matched_symbols=['159632.SZ', '513300.SH', '159819.SZ', '515880.SH', '510300.SH']

## Provider routing notes
- 无

## Runtime freshness diagnostics
- 详见 runtime_diagnostics.md
- total_elapsed_seconds: 143.001
- run_time_budget_exceeded: True
- max_quote_lag_seconds: 19600.656
- max_data_lag_seconds: 300.0
- 本轮刷新耗时超过预算，价格不宜用于盘中精确做T或高频操作。

## AKShare price records
- tech 159632.SZ 纳斯达克ETF华安: 市场已收盘；价格为收盘前/最后更新时间参考，不适合盘中做T判断
- tech 513300.SH 纳斯达克ETF华夏: 市场已收盘；价格为收盘前/最后更新时间参考，不适合盘中做T判断
- tech 159819.SZ 人工智能ETF易方达: 市场已收盘；价格为收盘前/最后更新时间参考，不适合盘中做T判断
- tech 515880.SH 通信ETF国泰: 市场已收盘；价格为收盘前/最后更新时间参考，不适合盘中做T判断
- tech 510300.SH 沪深300ETF华泰柏瑞: 市场已收盘；价格为收盘前/最后更新时间参考，不适合盘中做T判断

## AKShare quote freshness details
- 159632.SZ: market_status=closed, quote_time_raw=2026-05-18 15:34:03+08:00, quote_time_utc=2026-05-18T07:34:03+00:00, fetch_time_utc=2026-05-18T11:27:17.672986+00:00, age_seconds=14137, max_age_seconds=86400, is_stale=False
- 159632.SZ: market_status=closed, 市场已收盘，价格为收盘后/最后更新时间参考，不适合盘中做T判断
- 513300.SH: market_status=closed, quote_time_raw=2026-05-18 16:11:53+08:00, quote_time_utc=2026-05-18T08:11:53+00:00, fetch_time_utc=2026-05-18T11:27:47.127093+00:00, age_seconds=11867, max_age_seconds=86400, is_stale=False
- 513300.SH: market_status=closed, 市场已收盘，价格为收盘后/最后更新时间参考，不适合盘中做T判断
- 159819.SZ: market_status=closed, quote_time_raw=2026-05-18 15:34:21+08:00, quote_time_utc=2026-05-18T07:34:21+00:00, fetch_time_utc=2026-05-18T11:28:15.854391+00:00, age_seconds=14119, max_age_seconds=86400, is_stale=False
- 159819.SZ: market_status=closed, 市场已收盘，价格为收盘后/最后更新时间参考，不适合盘中做T判断
- 515880.SH: market_status=closed, quote_time_raw=2026-05-18 16:11:34+08:00, quote_time_utc=2026-05-18T08:11:34+00:00, fetch_time_utc=2026-05-18T11:28:44.769051+00:00, age_seconds=11886, max_age_seconds=86400, is_stale=False
- 515880.SH: market_status=closed, 市场已收盘，价格为收盘后/最后更新时间参考，不适合盘中做T判断
- 510300.SH: market_status=closed, quote_time_raw=2026-05-18 16:11:48+08:00, quote_time_utc=2026-05-18T08:11:48+00:00, fetch_time_utc=2026-05-18T11:29:14.216677+00:00, age_seconds=11872, max_age_seconds=86400, is_stale=False
- 510300.SH: market_status=closed, 市场已收盘，价格为收盘后/最后更新时间参考，不适合盘中做T判断

## AKShare / 数据质量问题
- 无

## 黄金手工价说明
黄金持仓参考价为用户手工录入价，不等同于国际现货金价；用于科技账户防守仓/潜在转科技资金的参考，实际操作前需核对账户内可卖价、手续费、点差和到账规则。

## 如果为否，原因
- 无

## 缺失价格列表
- 无

## stale 价格列表
- 无

## quote_time 缺失列表
- 无

## manual price records
- GOLD_CNY 黄金持仓参考价: price=1040.0, quote_time=2026-05-18T14:03:00+08:00, is_stale=False, source_note=用户手工录入：银行积存金/黄金理财估值价，需以后续实际账户可卖价为准, fee_note=手续费、点差、赎回到账规则未自动计算, asset_role=defense_or_potential_tech_funding

## warning
- 无

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
