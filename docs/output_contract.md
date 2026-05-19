# market_price_guard 输出契约

## 1. 总原则

market_price_guard 的输出文件是 GPT 项目指令依赖的接口契约。后续改动不得随意改名、删字段、改分组或改变 strict / blocking records 的语义。

- 动态价格不得写入项目指令，项目只能以用户本轮提供的最新输出为准。
- strict=2 或 blocking records 存在时，不得给具体操作建议。
- selected_provider=mock 或 usable_for_operation=false 时，不得用于具体操作。
- 所有 Markdown 使用 UTF-8 写入。
- CSV 使用项目当前中文友好编码，当前为 utf-8-sig。
- 所有报告不得输出实质性买卖建议、仓位动作或目标价。

## 2. index.md 契约

`index.md` 是每轮刷新后的入口摘要，不替代正式报告。

必须包含或等价表达：

- generated_at
- profile
- provider_mode
- provider_policy
- strict
- exit_code
- output_dir
- 可用于具体操作建议：是/否
- strict blocking records 摘要，如有
- provider_error 数量或摘要，如有
- stale 数量或摘要，如有
- quote_time_missing 数量或摘要，如有
- mock fallback not usable 数量或摘要，如有
- run_time_budget_exceeded，如有
- 核心价格覆盖摘要：
  - 能源账户核心价格：完整 / 不完整 / 未刷新
  - 科技账户核心价格：完整 / 不完整 / 未刷新
  - 黄金参考价：可用 / 不可用 / 未刷新
  - 非科技宽基：可用 / 不可用 / 未刷新
- runtime 摘要：
  - total_elapsed_seconds
  - max_quote_lag_seconds
  - oldest_quote_time
  - newest_quote_time
  - slow_provider_attempts 数量
- selected_provider 统计，如有
- fallback_used 数量，如有
- provider calls / cache hits，如有
- 推荐复制给项目的文件

推荐文件规则：

- energy: `energy_price_block.md`, `data_completeness_report.md`, `provider_health_report.md`, `runtime_diagnostics.md`
- tech: `tech_price_block.md`, `data_completeness_report.md`, `provider_health_report.md`, `runtime_diagnostics.md`
- all: `controller_price_summary.md`, `data_completeness_report.md`, `provider_health_report.md`, `runtime_diagnostics.md`
- diagnostic: `provider_health_report.md`, `runtime_diagnostics.md`, `data_completeness_report.md`, `prices_snapshot.csv`

## 2.1 profile 输出范围契约

不同 profile 的输出目录可以直接全选上传到对应 GPT 项目，因此必须避免项目边界污染。

- profile=tech 只生成：`index.md`, `tech_price_block.md`, `data_completeness_report.md`, `provider_health_report.md`, `runtime_diagnostics.md`, `prices_snapshot.csv`。
- profile=energy 只生成：`index.md`, `energy_price_block.md`, `data_completeness_report.md`, `provider_health_report.md`, `runtime_diagnostics.md`, `prices_snapshot.csv`。
- profile=all / controller 只生成：`index.md`, `controller_price_summary.md`, `data_completeness_report.md`, `provider_health_report.md`, `runtime_diagnostics.md`, `prices_snapshot.csv`。
- provider_policy=diagnostic 默认只生成：`index.md`, `data_completeness_report.md`, `provider_health_report.md`, `runtime_diagnostics.md`, `prices_snapshot.csv`。

禁止在 tech 输出目录生成 `energy_price_block.md` 或 `controller_price_summary.md`。
禁止在 energy 输出目录生成 `tech_price_block.md` 或 `controller_price_summary.md`。
禁止在 all / controller 输出目录默认生成能源/科技完整 price block。

## 3. tech_price_block.md 契约

必须保持固定分组：

- 纳指 / 海外科技ETF
- AI / 人工智能ETF
- 通信 / 科技ETF
- 黄金防守仓 / 潜在转科技资金
- 非科技宽基单独列示

固定归类：

- 159632.SZ、513300.SH -> 纳指 / 海外科技ETF
- 159819.SZ -> AI / 人工智能ETF
- 515880.SH -> 通信 / 科技ETF
- GOLD_CNY -> 黄金防守仓 / 潜在转科技资金
- 510300.SH -> 非科技宽基单独列示

禁止：

- GOLD_CNY 不得归入科技权益、AI、通信、纳指分组。
- 510300.SH 不得归入科技权益、AI、通信、纳指分组。
- 不得输出实质性交易建议。

每个标的建议包含：

- symbol
- name
- selected_provider/source
- price
- currency
- quote_time
- market_status
- is_stale
- stale_reason
- usable_for_operation

## 4. energy_price_block.md 契约

必须覆盖能源账户核心标的：

- 00883.HK 中海油H
- 601899.SH 紫金矿业A
- 601985.SH 中国核电
- 003816.SZ 中国广核

每个标的建议包含：

- symbol
- name
- selected_provider/source
- price
- currency
- quote_time
- market_status
- is_stale
- stale_reason
- usable_for_operation
- required_for_operation

如果 selected_provider=yfinance，应保留数据源限制说明或在 `data_completeness_report.md` 中引用。

## 5. controller_price_summary.md 契约

总控报告只能输出摘要，不得变成能源/科技完整明细仓库。

必须包含或等价表达：

- 能源账户核心价格是否完整
- 科技账户核心价格是否完整
- 黄金参考价是否可用
- 非科技宽基价格是否可用
- 是否允许资产配置判断
- 是否禁止具体操作判断
- 如果数据不可用，说明原因指向 `data_completeness_report.md` / `provider_health_report.md`

不得输出完整能源仓位明细、完整科技仓位明细、单只标的精确交易动作或实质性交易建议。

## 6. data_completeness_report.md 契约

必须包含或等价表达：

- 可用于具体操作建议：是/否
- strict 结果
- blocking records，如有
- provider_error
- stale
- quote_time_missing
- invalid_price
- mock fallback not usable
- yfinance 数据源限制，如果 yfinance 被使用
- `provider_health_report.md` 引用
- `runtime_diagnostics.md` 引用

## 7. provider_health_report.md 契约

必须包含或等价表达：

- provider_policy
- profile
- provider_mode
- 每个 symbol 的 effective provider chain
- provider attempts
- selected_provider
- fallback_used
- usable_for_operation
- exception_type / exception_message，如有
- elapsed_seconds，如有
- skipped providers，如有
- skip reason，如有
- provider call summary，如有：
  - function_name
  - call_count
  - cache_hits
  - returned_rows
  - matched_symbols
  - elapsed_seconds_first_call
  - exception_type / exception_message，如有

## 8. runtime_diagnostics.md 契约

必须包含或等价表达：

- run_start_time_utc
- run_end_time_utc
- total_elapsed_seconds
- profile
- provider_mode
- provider_policy
- strict
- per_provider_elapsed_seconds 或等价信息，如有
- slow_provider_attempts，如有
- provider_call_count_by_function，如有
- total_provider_calls，如有
- cache_hits，如有
- run_time_budget_exceeded
- max_quote_lag_seconds，如有
- oldest_quote_time
- newest_quote_time

## 9. prices_snapshot.csv 契约

当前稳定列：

- project
- symbol
- name
- market
- price
- currency
- source
- selected_provider
- quote_time
- fetch_time
- market_status
- is_stale
- stale_reason
- usable_for_operation
- required_for_operation
- quote_trust_tier
- usable_for_reference
- quote_purpose
- confirmation_required
- operation_blocking_reason
- reference_note

推荐未来列，当前不作为强制契约：

- asset_role
- fallback_used
- provider_policy
- profile

如果未来新增推荐列，应同步更新本文档和回归测试。

## 10. 禁止输出交易建议规则

所有报告中不得出现实质性交易建议。允许出现否定性或规则性表达，例如“不输出买卖建议”“不可用于具体操作建议”“不得用于做T判断”“禁止用于买入卖出”。

## 11. Quote Trust Tier Foundation

v0.6.3 追加价格用途分层字段，用于后续 reference / operation 分层；本版本不改变既有脚本、provider-policy、strict、freshness 或项目输出边界。

新增字段为附加字段，旧字段不得删除或重命名：

- quote_trust_tier: operation / reference / development。
- usable_for_reference: 是否可用于快速参考。
- quote_purpose: operation / reference，当前默认 operation。
- confirmation_required: 是否需要 operation-grade confirmation。
- operation_blocking_reason: 不可用于 operation 的原因。
- reference_note: 数据源或用途说明。

基础规则：

- AKShare ETF 在 price、quote_time、freshness 通过时为 operation。
- GOLD_CNY 手工价在当前配置允许且 freshness 通过时为 operation。
- yfinance A股 / 港股附加 reference note，披露其为公开 Yahoo Finance wrapper，不是官方交易所实时源；本版本不改变既有 strict 行为。
- yfinance ETF 如未来被调用，默认为 reference，usable_for_operation=false，confirmation_required=true。
- mock 默认为 development，不可用于真实 operation。
- provider_error、invalid_price、quote_time_missing 默认为 development，usable_for_reference=false，usable_for_operation=false，confirmation_required=true。

报告追加要求：

- index.md 保留原有“可用于具体操作建议”结论，并追加 Quote trust summary。
- data_completeness_report.md 保留 strict / blocking records 语义，并追加 Quote trust tier diagnostics。
- tech_price_block.md / energy_price_block.md 可追加 quote_trust_tier、usable_for_reference、confirmation_required，但不得改变旧分组和旧字段。
- provider_health_report.md 可追加 quote_trust_tier、usable_for_reference、confirmation_required、reference_note，但不得破坏 provider attempts、selected_provider、fallback_used、usable_for_operation。

## 12. Fast Reference Mode for Tech ETF

`quote_purpose=reference` 是快速参考通道，不改变默认 operation 通道。

科技 reference 输出目录：

- `outputs_tech_reference_latest`

文件范围与 tech profile 隔离规则一致：

- 必须生成 `index.md`, `tech_price_block.md`, `data_completeness_report.md`, `provider_health_report.md`, `runtime_diagnostics.md`, `prices_snapshot.csv`。
- 不得生成 `energy_price_block.md` 或 `controller_price_summary.md`。

reference 模式语义：

- `quote_purpose=reference`。
- 科技 ETF fast reference effective chain 可为 `yfinance -> akshare -> mock`。
- yfinance ETF 必须为 `quote_trust_tier=reference`。
- yfinance ETF 必须 `usable_for_reference=true`，前提是 price / quote_time 基本有效。
- yfinance ETF 必须 `usable_for_operation=false`。
- yfinance ETF 必须 `confirmation_required=true`。
- `index.md` 和 `data_completeness_report.md` 必须说明本轮不可用于具体操作建议；如需 operation-grade confirmation，应运行 `run_tech_fast_strict.ps1`。

默认 operation 模式保持不变：

- `run_tech_fast_strict.ps1` 不得改成 reference。
- `outputs_tech_latest` 语义不变。
- operation strict 不得因 reference-grade quote 而通过。
