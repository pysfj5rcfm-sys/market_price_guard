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

# Reconciliation UAT (v0.7.1)

检查：
- `price_reconciliation_report.md` 存在；
- aligned / minor_diff / warning_diff / major_diff 阈值测试通过；
- `0_upload_bundle.md` 包含 reconciliation summary；
- `debug_bundle.md` 包含 reconciliation details；
- `operation_candidate_agreed=true` 不改变 strict 结果；
- reference-grade 不得因为多源一致性被写成 operation-grade；
- 报告不输出实质性交易建议。

# Tech Reconcile UAT (v0.7.1.1)

# Symbol Registry / Universe UAT (v0.7.1.2)

Run:
```powershell
.\scripts\run_tech_watchlist.ps1
.\scripts\run_tech_scan_ai.ps1
```

Check:
- `outputs_tech_watchlist_latest/0_upload_bundle.md` exists.
- `outputs_tech_watchlist_latest/candidate_watchlist_report.md` exists.
- `outputs_tech_scan_ai_latest/0_upload_bundle.md` exists.
- `outputs_tech_scan_ai_latest/scan_universe_report.md` exists.
- Watchlist and scan scripts do not use `--strict`.
- Candidate and scan symbols remain `required_for_operation=false`.
- Candidate and scan provider errors do not block core operation strict.
- Unknown symbols appear in `unsupported_symbols_report.md` with `suggested_fix`.
- Reports state that scan/watchlist output is not for concrete operation recommendations.

# Tech Reconcile UAT (v0.7.1.1)

运行：

```powershell
.\scripts\run_tech_reconcile.ps1
```

检查：
- `outputs_tech_reconcile_latest/0_upload_bundle.md` 存在；
- `outputs_tech_reconcile_latest/debug_bundle.md` 存在；
- `outputs_tech_reconcile_latest/price_reconciliation_report.md` 存在；
- `quote_purpose=reference`；
- `reconcile_mode=full`；
- Eastmoney Direct / yfinance / AKShare attempts 可见；
- 如果仍为 `single_source_only`，报告必须说明失败或跳过原因；
- Eastmoney Direct 仍不得显示为 operation-grade；
- 日常上传优先 `0_upload_bundle.md`，异常再补 `debug_bundle.md`。
## Minute Bars Probe UAT

Run:

```powershell
.\scripts\run_tech_minute_probe.ps1
```

Check:

- `outputs_tech_minute_probe_latest/0_upload_bundle.md` exists.
- `outputs_tech_minute_probe_latest/debug_bundle.md` exists.
- `prices_snapshot.csv` contains `minute_bars_available`, `minute_bar_provider`, `minute_bar_interval`, `minute_bar_count`, `minute_bar_latest_time`, `minute_bar_status`, `minute_bar_validation_status`, and `minute_bar_missing_reason`.
- `0_upload_bundle.md` contains `Minute Bars Probe Summary`.
- `debug_bundle.md` contains `Minute Bars Probe Detail`.
- `data_completeness_report.md` contains `Minute Bars Completeness`.
- Minute bars are diagnostic only and do not change strict or operation readiness.
- VWAP and intraday derived fields are not calculated in v0.7.2a.

## Tech Operation Candidates UAT

Run:

```powershell
.\scripts\run_tech_operation_candidates.ps1
```

Check:

- `outputs_tech_operation_candidates_latest/0_upload_bundle.md` exists.
- `outputs_tech_operation_candidates_latest/debug_bundle.md` exists.
- `outputs_tech_operation_candidates_latest/operation_candidate_report.md` exists.
- Empty `tech_operation_candidates` universe exits successfully with `empty_universe`.
- Operation-candidate records keep `required_for_operation=false`.
- Operation-candidate records keep `usable_for_operation=false`.
- Operation-candidate records keep `affect_core_strict=false`.
- Operation-candidate failures do not affect `run_tech_fast_strict.ps1`.
- The output states it is not usable for concrete operation recommendations.

Additional v0.7.2a.1 checks:

- `run_tech_scan_ai.ps1` keeps 26 scan symbols in `prices_snapshot.csv`.
- ETF / QDII ETF scan candidates attempt AKShare `fund_etf_spot_em`.
- A-share stock scan candidates attempt AKShare stock spot helpers.
- Scan records remain `required_for_operation=false` and `usable_for_operation=false`.
- `run_tech_minute_probe.ps1` attempts AKShare ETF minute bars through `fund_etf_hist_min_em`.
- If minute bars are available, `minute_bars_snapshot.csv` is generated and listed in `index.md`.

## Reference Intraday Metrics UAT

Run:

```powershell
.\scripts\run_tech_intraday_metrics.ps1
```

Check:

- `outputs_tech_intraday_latest/0_upload_bundle.md` exists.
- `outputs_tech_intraday_latest/intraday_metrics_snapshot.csv` exists.
- `outputs_tech_intraday_latest/reference_vwap_report.md` exists.
- Missing `minute_bars_snapshot.csv` is reported as not calculable rather than a script failure.
- `GOLD_CNY` is marked not supported for intraday metrics.
- Operation candidates remain `usable_for_operation=false`.
- Reference VWAP does not change strict or operation readiness.
- No execution instructions are generated.
- Minute-bar availability does not change strict or operation readiness.
- v0.7.2a.2: if AKShare minute probe fails, Eastmoney Direct minute probe is attempted.
- Debug output includes `eastmoney_secid`, `provider_attempted`, and `provider_success`.
- Eastmoney minute bars remain diagnostic/reference only.
