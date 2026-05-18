# 数据完整度报告

可用于具体操作建议：是

本工具不做自动交易，不输出买卖建议，只输出价格事实、数据源、时间戳、市场状态和数据完整度。

行情源健康状态详见 provider_health_report.md。

## Strict blocking records
- 无

## Provider diagnostics
- 无 AKShare 记录

## Provider routing notes
- 00883.HK: primary failed but fallback selected; selected_provider=yfinance; selection_reason=selected_provider_returned_usable_price
- 00883.HK: 使用 yfinance secondary provider；数据源限制：open-source Yahoo Finance public API wrapper; research/educational use; not official exchange feed
- 601899.SH: primary failed but fallback selected; selected_provider=yfinance; selection_reason=selected_provider_returned_usable_price
- 601899.SH: 使用 yfinance secondary provider；数据源限制：open-source Yahoo Finance public API wrapper; research/educational use; not official exchange feed
- 601985.SH: primary failed but fallback selected; selected_provider=yfinance; selection_reason=selected_provider_returned_usable_price
- 601985.SH: 使用 yfinance secondary provider；数据源限制：open-source Yahoo Finance public API wrapper; research/educational use; not official exchange feed
- 003816.SZ: primary failed but fallback selected; selected_provider=yfinance; selection_reason=selected_provider_returned_usable_price
- 003816.SZ: 使用 yfinance secondary provider；数据源限制：open-source Yahoo Finance public API wrapper; research/educational use; not official exchange feed

## Runtime freshness diagnostics
- 详见 runtime_diagnostics.md
- total_elapsed_seconds: 75.403
- run_time_budget_exceeded: True
- max_quote_lag_seconds: 16258.752
- max_data_lag_seconds: 300.0
- 本轮刷新耗时超过预算，价格不宜用于盘中精确做T或高频操作。

## AKShare price records
- 无

## AKShare quote freshness details
- 无

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
- 无

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
