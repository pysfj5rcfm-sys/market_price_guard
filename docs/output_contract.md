# market_price_guard 输出契约 v2

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

## 13. Output Contract v2: Upload / Debug Bundle

每个 relevant output directory 必须额外生成：

- `0_upload_bundle.md`
- `debug_bundle.md`

原始报告仍必须保留；bundle 只是聚合入口，不替代 `index.md`、price block、`data_completeness_report.md`、`provider_health_report.md`、`runtime_diagnostics.md` 或 `prices_snapshot.csv`。

### 13.1 Quote Purpose

- `operation`: 用于具体操作前的数据完整度与 operation-grade confirmation。
- `reference`: 用于快速参考，不可用于具体操作建议或高精度执行型判断。

### 13.2 Quote Trust Tier

- `operation`: price、quote_time、freshness、provider_health 与 strict 语义满足当前 operation 要求。
- `reference`: 可快速参考，但需要 operation confirmation。
- `development`: mock、provider_error、invalid_price、quote_time_missing 或测试用途记录。

### 13.3 Required Fields

bundle、CSV 和关键报告必须保留或等价表达：

- quote_purpose
- quote_trust_tier
- usable_for_reference
- usable_for_operation
- confirmation_required
- operation_blocking_reason
- reference_note
- selected_provider
- price
- currency
- quote_time
- is_stale
- stale_reason
- required_for_operation

### 13.4 0_upload_bundle.md Contract

`0_upload_bundle.md` 是日常上传给 GPT 项目的最小包。必须包含：

- generated_at、profile、provider_mode、provider_policy、quote_purpose、strict、exit_code、output_dir。
- 可用于快速参考：是/否。
- 可用于具体操作建议：是/否。
- 当前用途级别：reference-only / operation-ready / operation-blocked / diagnostic-only。
- 数据完整度摘要、blocking records 摘要、Quote Trust Tier 摘要。
- 对应 profile 的核心 price block 或 controller summary 摘要。
- reference / operation 使用提示。
- debug_bundle.md 补充上传条件。

`quote_purpose=reference` 时必须明确不可用于具体操作建议。`quote_purpose=operation` 且 strict / operation-grade 通过时，才可进入完整操作级分析。

### 13.5 debug_bundle.md Contract

`debug_bundle.md` 仅在排障时上传。必须包含：

- Provider Health 摘要。
- Runtime Diagnostics 摘要。
- prices_snapshot 关键明细摘要。
- Blocking / Error 摘要。
- provider attempts、selected_provider、fallback_used、skipped providers、provider_error、exception_type / exception_message、from_cache、call_count / cache_hits、matched_symbols、usable_for_operation、usable_for_reference、quote_trust_tier、confirmation_required。

### 13.6 Profile-scoped Bundle

- `outputs_tech_latest`: tech operation bundle。
- `outputs_tech_reference_latest`: tech reference bundle。
- `outputs_energy_latest`: energy operation bundle。
- `outputs_all_latest`: controller summary bundle。
- `outputs_diagnostic`: diagnostic bundle。

各目录继续遵守 profile 输出隔离规则。总控 bundle 只包含摘要，不包含能源/科技完整逐标的 price block。

### 13.7 No Trading Advice

所有报告和 bundle 均不得输出实质性交易建议。允许否定性或规则性表达，例如“不可用于具体操作建议”“禁止用于买入卖出”“不输出买卖建议”。

### 13.8 Eastmoney Direct Provider

`eastmoney_direct` 是 v0.7.0 新增的快速指定标的报价 provider，覆盖 A股 ETF 与部分 A股股票。它属于 reference / operation-candidate：

- `quote_trust_tier=reference`
- `usable_for_reference=true`，前提是 price 与 quote_time 基本有效
- `usable_for_operation=false`
- `confirmation_required=true`
- `operation_blocking_reason=reference_tier_requires_operation_confirmation`

Eastmoney Direct 使用东方财富公开网页行情接口路径，不是官方交易所实时行情源。它不得单独作为 operation-grade 数据，也不得让 operation strict 放行。若被选中，`0_upload_bundle.md`、`debug_bundle.md`、`provider_health_report.md` 与 `data_completeness_report.md` 必须披露 source limitation。

### 13.9 price_reconciliation_report.md Contract

`price_reconciliation_report.md` 是 v0.7.1 新增的多源价格差异检查报告。它必须包含或等价表达：

- `source_agreement_status`
- `compared_sources`
- `reference_source`
- `candidate_source`
- `price_diff_abs`
- `price_diff_pct`
- `quote_time_gap_seconds`
- `operation_candidate_agreed`
- `reconciliation_note`

多源一致性检查只用于数据质量诊断，不自动构成交易建议，不自动提升 reference-grade 到 operation-grade。即使 `operation_candidate_agreed=true`，operation strict 仍以原有 strict / freshness / quote_trust_tier / usable_for_operation 规则为准。

### 13.11 Symbol Registry And Universe Contract

`config/symbol_registry.yaml` is the canonical metadata registry for symbols. `config/universes/*.yaml` selects the current run scope.

Required universe fields:
- `name`
- `profile`
- `universe_type`
- `quote_purpose`
- `symbols`

Supported `universe_type` values:
- `core_holdings`: may affect operation strict when a symbol is `required_for_operation=true`
- `candidate_watchlist`: defaults to `required_for_operation=false`
- `scan_universe`: reference scan pool, never operation strict blocking
- `controller_summary`: summary-only controller scope

Additional output contracts:
- `unsupported_symbols_report.md`: unregistered or invalid symbols, suggested fixes, never strict-blocking
- `candidate_watchlist_report.md`: candidate price facts and reference usability
- `scan_universe_report.md`: scan price facts and data status

When the registry layer is active, `0_upload_bundle.md` and `debug_bundle.md` must include `universe_name`, `universe_type`, and unsupported symbol counts.

### 13.12 API Field Capability Matrix

`docs/api_field_capability_matrix.md` is an audit document, not an output contract. It describes current provider and guard field capability.

If a future version adds fields from the matrix into `prices_snapshot.csv`, bundles, or reports, this output contract must be upgraded separately.

### 13.13 Base Quote Fields Contract

v0.7.1.4 standardizes provider-supplied base quote fields as additive output fields:

- `last_price`
- `prev_close`
- `open_price`
- `high_price`
- `low_price`
- `volume`
- `amount`
- `price_change`
- `price_change_pct`
- `amplitude_pct`
- `base_quote_completeness`
- `base_quote_missing_fields`
- `base_quote_fields_available_count`
- `base_quote_fields_missing_count`
- `exchange`
- `country_market`
- `trading_calendar`

These fields are auxiliary quote diagnostics. Field completeness does not equal operation-grade permission. Operation use still depends on `quote_trust_tier`, `usable_for_operation`, strict blocking records, freshness, and provider health.

`price` remains the legacy primary price field. `last_price` is an additive normalized alias and must not replace `price` in old consumers without a contract update. The legacy `market` field is retained to avoid freshness regression. `exchange`, `country_market`, and `trading_calendar` provide more precise market metadata for future modules.

Missing base quote fields must not automatically change strict exit code in v0.7.1.4. If future versions make any base quote field operation-blocking, this contract and UAT must be updated first.

### 13.14 Compact Base Quote Table Contract

v0.7.1.5 adds compact base quote tables to upload bundles and project price blocks. This is a presentation enhancement only:

- `0_upload_bundle.md` shows a compact base quote snapshot for tech, energy, reference, watchlist, and scan outputs.
- `outputs_all_latest/0_upload_bundle.md` keeps controller output summarized and must not include full tech/energy execution tables.
- `tech_price_block.md` and `energy_price_block.md` append a `Base Quote Fields` section without removing existing price guard fields.
- `candidate_watchlist_report.md` and `scan_universe_report.md` show compact candidate/scan base quote tables.
- `debug_bundle.md` includes `Base Quote Field Sources` and lightweight `Provider Capability Notes`.

The compact tables do not change CSV schema, strict logic, freshness, provider trust tier, or operation/reference semantics. `volume` and `amount` remain provider raw units unless explicit unit normalization is available. The tables must not output trading advice.

### 13.15 Provider Capability Report Contract

v0.7.1.6 adds `provider_capability_report.md` to each output directory. The report is diagnostic only and must not change strict, provider chain, freshness, trust tier, or operation/reference semantics.

Required sections:
- `Runtime Context`
- `Provider Capability Summary`
- `Field Capability Matrix By Provider`
- `Symbol Field Quality`
- `Safe Usage Notes`

Required concepts:
- field status, such as `supported`, `provider_dependent`, `supported_raw_unit`, `unit_unknown`, `not_validated`, `missing`, and `not_implemented`
- unit and unit confidence
- `comparable_across_providers`
- `operation_fit`
- `reference_fit`

`prices_snapshot.csv` may include the following additive diagnostic fields:
- `field_quality_summary`
- `field_validation_status`
- `volume_unit`
- `amount_unit`
- `volume_unit_confidence`
- `amount_unit_confidence`
- `volume_comparable_across_providers`
- `amount_comparable_across_providers`
- `price_change_pct_comparable`
- `base_quote_comparable_score`
- `provider_capability_status`
- `provider_capability_notes`

`0_upload_bundle.md` should only include compact Field Quality Notes and reference `debug_bundle.md` / `provider_capability_report.md` for details.

`debug_bundle.md` must include a Provider Capability Summary and current field-quality risks.

Capability fields are not operation-grade permissions. Field completeness does not upgrade a quote from reference to operation. `volume` and `amount` must not be compared across providers until unit confidence and comparability are explicitly validated. `bid/ask`, `turnover_rate`, `minute_bars`, VWAP, and QDII premium remain not validated or not implemented in v0.7.1.6.

### 13.16 Scan Ranking Contract

v0.7.1.7 adds basic review-priority ranking for `candidate_watchlist` and `scan_universe` outputs. It is not trading advice and must not change strict, freshness, provider chain, quote trust tier, or operation/reference semantics.

Additive CSV fields:
- `rankable`
- `rank_exclusion_reason`
- `scan_status`
- `watch_priority`
- `scan_score_basic`
- `data_quality_score`
- `momentum_score_basic`
- `field_reliability_score`
- `liquidity_score_basic`
- `reconciliation_score`
- `scan_score_notes`

Report requirements:
- `scan_universe_report.md` includes `Scan Universe Basic Ranking`, `Scan Summary`, `Basic Ranking Table`, `Not Rankable`, and safety notes.
- `candidate_watchlist_report.md` includes `Watchlist Review Priority`.
- `0_upload_bundle.md` includes `Scan Priority Summary` and `Top Scan Candidates` for scan/watchlist outputs.
- `debug_bundle.md` includes `Scan Ranking Trace`.
- `data_completeness_report.md` includes `Scan Ranking Summary`.

Ranking is only a review-priority queue. It must not emit execution instructions, preferred actions, action hints, target prices, or entry/stop labels. `volume` and `amount` must not inflate ranking when provider comparability flags are false.

### 13.10 Tech Reconcile Output

`outputs_tech_reconcile_latest/` 是 v0.7.1.1 新增的科技多源对账目录：

- `quote_purpose=reference`
- `reconcile_mode=full`
- 生成 `0_upload_bundle.md`、`debug_bundle.md`、`price_reconciliation_report.md`、`provider_health_report.md`、`runtime_diagnostics.md`、`tech_price_block.md`、`prices_snapshot.csv`
- 不生成 `energy_price_block.md`
- 不生成 `controller_price_summary.md`

最小上传口径：日常只上传 `0_upload_bundle.md`；当出现 strict 阻断、provider_error、stale、quote_time_missing、major_diff、run_time_budget_exceeded 或报告冲突时，再补充 `debug_bundle.md`。原始报告用于人工核查，不是日常首选上传文件。
### 13.17 Minute Bars Probe Contract

v0.7.2a adds an optional Minute Bars Ingestion Probe. The probe is diagnostic only and must not change strict, freshness, provider chain, quote trust tier, usable_for_operation, or operation/reference semantics.

`prices_snapshot.csv` appends these stable fields:

- `minute_bars_available`
- `minute_bar_provider`
- `minute_bar_interval`
- `minute_bar_count`
- `minute_bar_latest_time`
- `minute_bar_fetch_time`
- `minute_bar_status`
- `minute_bar_validation_status`
- `minute_bar_missing_reason`
- `minute_bar_notes`

`0_upload_bundle.md` includes `Minute Bars Probe Summary` when minute probing is enabled or probe fields are present. The summary must state that minute bars are diagnostic in v0.7.2a, do not change strict or operation readiness, and do not calculate VWAP or intraday derived fields.

`debug_bundle.md` includes `Minute Bars Probe Detail` with provider attempted, status, interval, count, latest time, fetch time, validation status, missing reason, and notes.

`data_completeness_report.md` includes `Minute Bars Completeness` with available, unavailable, not supported, provider error, symbol not found, stale, and provider summaries. Missing minute bars must not become an operation blocking condition in v0.7.2a.

`provider_capability_report.md` includes `Minute Bars Capability`. `mock` may be `supported_for_tests`; `manual` is `not_supported`; live providers without a guarded implementation should be reported as `not_implemented`, `not_validated`, or equivalent.

Optional `minute_bars_snapshot.csv` may be generated when actual bars are available. It is a debug/probe artifact, not the daily minimal upload file.

v0.7.2a does not compute VWAP, day position, chase risk, buy zones, QDII premium, action hints, preferred actions, or allowed advice levels.

### 13.18 AKShare Scan Quote And Minute Probe Coverage

v0.7.2a.1 expands AKShare real-data coverage for reference/diagnostic scan paths without changing operation semantics.

`tech_scan_ai` scan records may attempt:

- ETF / QDII ETF spot quote through AKShare `fund_etf_spot_em`.
- A-share stock spot quote through AKShare stock spot helpers.

Scan records must remain:

- `required_for_operation=false`
- `usable_for_operation=false`
- reference / scan inputs, not operation holdings

`minute_bars_snapshot.csv`, when generated, contains:

- `symbol`
- `name`
- `provider`
- `interval`
- `timestamp`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`
- `validation_status`
- `notes`

`debug_bundle.md` Minute Bars Probe Detail should include provider attempted, provider success, normalized symbol, status, interval, count, latest time, fetch time, validation status, missing reason, and notes.

AKShare ETF minute bars use `fund_etf_hist_min_em` in the optional minute probe path only. Minute-bar availability must not upgrade trust tier, change strict, or change operation readiness.

### 13.19 Eastmoney Direct Minute Probe Contract

v0.7.2a.2 adds Eastmoney Direct as a fallback provider for the optional minute-bars probe.

Minute probe details should include:

- `provider_attempted`
- `provider_success`
- `normalized_symbol`
- `eastmoney_secid`
- `minute_bar_status`
- `minute_bar_interval`
- `minute_bar_count`
- `minute_bar_latest_time`
- `minute_bar_validation_status`
- `minute_bar_missing_reason`
- `minute_bar_notes`

Eastmoney Direct successful bars use `minute_bar_provider=eastmoney_direct` and `minute_bar_validation_status=provider_dependent` or equivalent. `minute_bars_snapshot.csv` may contain rows with `provider=eastmoney_direct`.

Eastmoney Direct minute bars are diagnostic/reference only. They must not upgrade trust tier, change strict, change freshness, or change operation readiness.

### 13.20 YFinance Reference Minute Fallback Contract

v0.7.2a.2b adds YFinance as the third optional minute-bars fallback after AKShare and Eastmoney Direct both fail to return usable bars.

Minute probe details may include:

- `yfinance_ticker`
- `yfinance_status`
- `yfinance_reason`
- `yfinance_error_type`
- `yfinance_error_message`

YFinance successful bars use `minute_bar_provider=yfinance` and `minute_bar_validation_status=provider_dependent`. `minute_bars_snapshot.csv` may contain rows with `provider=yfinance`.

YFinance minute bars are diagnostic/reference only. They must not upgrade trust tier, change strict, change freshness, change usable_for_operation, or calculate VWAP.
