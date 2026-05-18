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
- `outputs_tech_latest/tech_price_block.md` 存在。
- `outputs_tech_latest/data_completeness_report.md` 存在。
- `outputs_tech_latest/provider_health_report.md` 存在。
- `outputs_tech_latest/runtime_diagnostics.md` 存在。
- `tech_price_block.md` 包含固定分组。
- `GOLD_CNY` 在黄金防守仓。
- `510300.SH` 在非科技宽基单独列示。
- `data_completeness_report.md` 显示 strict / 可操作性。
- `provider_health_report.md` 显示 selected_provider。
- `runtime_diagnostics.md` 显示耗时。
- 报告不输出实质性交易建议。

## 3. 能源账户 UAT

运行：

```powershell
.\scripts\run_energy_fast_strict.ps1
```

检查：

- `outputs_energy_latest/index.md` 存在。
- `outputs_energy_latest/energy_price_block.md` 存在。
- 能源核心标的覆盖 `00883.HK`、`601899.SH`、`601985.SH`、`003816.SZ`。
- selected_provider 可见。
- yfinance 数据源限制在报告中可见，如果 yfinance 被使用。
- strict=2 时，项目不得给具体操作。
- strict=0 时，仍要检查 quote_time / stale / runtime。
- 报告不输出实质性交易建议。

## 4. 总控项目 UAT

运行：

```powershell
.\scripts\run_all_fast_strict.ps1
```

检查：

- `outputs_all_latest/index.md` 存在。
- `outputs_all_latest/controller_price_summary.md` 存在。
- 只输出摘要。
- 不输出能源/科技完整明细。
- 能看出能源 / 科技 / 黄金 / 非科技宽基状态。
- strict 结果明确。
- 报告不输出实质性交易建议。

## 5. 诊断模式 UAT

运行：

```powershell
.\scripts\run_diagnostic.ps1
```

检查：

- `outputs_diagnostic/index.md` 存在。
- `provider_health_report.md` 存在。
- `runtime_diagnostics.md` 存在。
- provider_policy=diagnostic 可见。
- 诊断模式可能较慢，应能从 runtime_diagnostics.md 看到耗时。
- 报告不输出实质性交易建议。

## 6. 回归标准

通过标准：

- pytest 全部通过。
- 脚本能运行。
- latest 输出目录生成。
- index.md 存在。
- 关键报告存在。
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
