# market_price_guard UAT 检查清单

## 1. UAT 总原则

- UAT 不要求每轮 strict 都返回 0。
- strict=2 但报告正确阻断，也可以是通过。
- UAT 失败指：脚本崩溃、报告缺失、格式破坏、错误分组、缺少 blocking records、输出实质性交易建议等。
- 数据不可用是市场/数据源状态，不等于系统失败。

## 2. 科技账户 UAT

运行：

```powershell
.\scripts\run_tech_fast_strict.ps1
```

检查：

- `outputs_tech_latest/index.md` 存在。
- `outputs_tech_latest/0_upload_bundle.md` 存在。
- `outputs_tech_latest/debug_bundle.md` 存在。
- `outputs_tech_latest/tech_price_block.md` 存在。
- `outputs_tech_latest/data_completeness_report.md` 存在。
- `outputs_tech_latest/provider_health_report.md` 存在。
- `outputs_tech_latest/runtime_diagnostics.md` 存在。
- `tech_price_block.md` 包含固定分组。
- `outputs_tech_latest` 不包含 `energy_price_block.md`。
- `outputs_tech_latest` 不包含 `controller_price_summary.md`。
- `GOLD_CNY` 在黄金防守仓。
- `510300.SH` 在非科技宽基单独列示。
- `data_completeness_report.md` 显示 strict / 可操作性。
- `provider_health_report.md` 显示 selected_provider。
- `runtime_diagnostics.md` 显示耗时。
- 报告不输出实质性交易建议。
- `0_upload_bundle.md` 包含 tech price block 核心摘要。
- quote_purpose=operation 可见。

## 3. 能源账户 UAT

运行：

```powershell
.\scripts\run_energy_fast_strict.ps1
```

检查：

- `outputs_energy_latest/index.md` 存在。
- `outputs_energy_latest/0_upload_bundle.md` 存在。
- `outputs_energy_latest/debug_bundle.md` 存在。
- `outputs_energy_latest/energy_price_block.md` 存在。
- `outputs_energy_latest` 不包含 `tech_price_block.md`。
- `outputs_energy_latest` 不包含 `controller_price_summary.md`。
- 能源核心标的覆盖 `00883.HK`、`601899.SH`、`601985.SH`、`003816.SZ`。
- selected_provider 可见。
- yfinance 数据源限制在报告中可见，如果 yfinance 被使用。
- strict=2 时，项目不得给具体操作。
- strict=0 时，仍要检查 quote_time / stale / runtime。
- 报告不输出实质性交易建议。
- `0_upload_bundle.md` 包含 energy price block 核心摘要。

## 4. 总控项目 UAT

运行：

```powershell
.\scripts\run_all_fast_strict.ps1
```

检查：

- `outputs_all_latest/index.md` 存在。
- `outputs_all_latest/0_upload_bundle.md` 存在。
- `outputs_all_latest/debug_bundle.md` 存在。
- `outputs_all_latest/controller_price_summary.md` 存在。
- `outputs_all_latest` 不包含 `energy_price_block.md`。
- `outputs_all_latest` 不包含 `tech_price_block.md`。
- 只输出摘要。
- 不输出能源/科技完整明细。
- 能看出能源 / 科技 / 黄金 / 非科技宽基状态。
- strict 结果明确。
- 报告不输出实质性交易建议。
- `0_upload_bundle.md` 包含 controller summary 核心摘要。
- `0_upload_bundle.md` 不包含能源/科技完整逐标的 price block。

## 5. 诊断模式 UAT

运行：

```powershell
.\scripts\run_diagnostic.ps1
```

检查：

- `outputs_diagnostic/index.md` 存在。
- `outputs_diagnostic/0_upload_bundle.md` 存在。
- `outputs_diagnostic/debug_bundle.md` 存在。
- `provider_health_report.md` 存在。
- `runtime_diagnostics.md` 存在。
- `outputs_diagnostic` 不包含能源/科技/总控项目块。
- provider_policy=diagnostic 可见。
- 诊断模式可能较慢，应能从 runtime_diagnostics.md 看到耗时。
- 报告不输出实质性交易建议。
- diagnostic bundle 明确是排障用途，不直接作为操作依据。

## 6. 回归标准

Quote Trust Tier 检查：

- `prices_snapshot.csv` 保留旧关键列，并追加 quote_trust_tier、usable_for_reference、quote_purpose、confirmation_required、operation_blocking_reason、reference_note。
- `index.md` 包含 Quote trust summary，且原有“可用于具体操作建议”结论仍存在。
- `data_completeness_report.md` 包含 Quote trust tier diagnostics，且 strict / blocking records 语义未改变。
- 科技账户 UAT 仍通过；tech_price_block.md 的固定分组和 GOLD_CNY / 510300.SH 分类边界不得改变。
- reference-grade 不得被描述成 operation-grade；yfinance ETF 如未来出现，不得用于 operation strict。

Tech Reference UAT：

运行：

```powershell
.\scripts\run_tech_fast_reference.ps1
```

检查：

- `outputs_tech_reference_latest/index.md` 存在。
- `outputs_tech_reference_latest/0_upload_bundle.md` 存在。
- `outputs_tech_reference_latest/debug_bundle.md` 存在。
- `outputs_tech_reference_latest/tech_price_block.md` 存在。
- `outputs_tech_reference_latest` 不包含 `energy_price_block.md` 或 `controller_price_summary.md`。
- `quote_purpose=reference` 可见。
- ETF 可由 yfinance 提供 reference-grade 参考价。
- `usable_for_operation=false` 和 `confirmation_required=true` 可见。
- 报告明确不可用于具体操作建议。
- 报告不输出实质性交易建议。
- `0_upload_bundle.md` 显示 reference-only / 快速参考。
- `debug_bundle.md` 包含 provider / runtime / snapshot 摘要。

通过标准：

- pytest 全部通过。
- 脚本能运行。
- latest 输出目录生成。
- index.md 存在。
- 关键报告存在。
- profile 输出隔离未破坏。
- 关键分组未破坏。
- strict 语义未破坏。
- 无实质性交易建议。

失败标准：

- 脚本语法错误。
- 程序 exit code=1。
- 必要报告缺失。
- tech 分组错误。
- GOLD_CNY / 510300 分类错误。
- controller 输出完整明细。
- 缺少 strict / blocking 说明。
- 输出实质性交易建议。
# Eastmoney Direct UAT (v0.7.0)

运行：

```powershell
.\scripts\run_tech_fast_reference.ps1
```

检查：
- reference mode 中可尝试 `eastmoney_direct`；
- 如果 `eastmoney_direct` 被选中，必须显示 `quote_trust_tier=reference`、`usable_for_operation=false`、`confirmation_required=true`；
- `0_upload_bundle.md` 必须明确不可用于具体操作建议；
- `debug_bundle.md` / `provider_health_report.md` 必须包含 `eastmoney_direct` 的 provider 明细；
- operation strict 输出不得因为 `eastmoney_direct` 改变放行标准。
