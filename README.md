# market_price_guard

价格实时获取与新鲜度校验工具，用于在理财项目之间共享价格事实、数据源、时间戳、市场状态和数据完整度提示。

本工具不提供买卖建议，不做自动交易，只做价格事实与数据完整度检查。不做仓位市值计算。

## 日常使用

一键脚本会自动定位项目根目录，并优先使用 `.venv\Scripts\python.exe`。如果未找到 `.venv`，请先创建虚拟环境并安装依赖。

能源账户日常快速刷新：
```powershell
.\scripts\run_energy_fast_strict.ps1
```

科技账户日常快速刷新：
```powershell
.\scripts\run_tech_fast_strict.ps1
```

投资咨询 / 总控项目全量快速刷新：
```powershell
.\scripts\run_all_fast_strict.ps1
```

完整 provider 诊断：
```powershell
.\scripts\run_diagnostic.ps1
```

离线自检：
```powershell
.\scripts\run_mock_strict.ps1
```

每次运行后先查看入口摘要：
```powershell
Get-Content outputs_energy_latest\index.md -Encoding UTF8
Get-Content outputs_tech_latest\index.md -Encoding UTF8
Get-Content outputs_all_latest\index.md -Encoding UTF8
```

exit code 说明：
- exit code=0：strict 通过，可根据报告进一步分析。
- exit code=2：strict 阻断，不得用于具体操作建议。
- exit code=1：程序错误，需要排查。

报告说明：
- `index.md` 是入口摘要。
- `data_completeness_report.md` 是正式数据完整度报告。
- `provider_health_report.md` 是行情源健康报告。
- `runtime_diagnostics.md` 是运行耗时报告。
- `outputs_tech_latest` 可直接全选上传到科技项目；目录内只包含科技项目需要的价格块和公共诊断报告。
- `outputs_energy_latest` 可直接全选上传到能源项目；目录内只包含能源项目需要的价格块和公共诊断报告。
- `outputs_all_latest` 可直接全选上传到总控项目；目录内只包含总控摘要和公共诊断报告。
- `outputs_diagnostic` 用于排障，不直接作为项目操作依据。

Windows PowerShell 查看中文报告建议：
```powershell
chcp 65001
Get-Content outputs_energy_latest\index.md -Encoding UTF8
```

也可以使用 VS Code 打开 Markdown 报告。

## Provider Mode

默认使用 mock 模式，不访问网络：

```bash
python -m market_price_guard.main --provider-mode mock --strict
```

live 模式才调用 AKShare 网络接口：

```bash
python -m market_price_guard.main --provider-mode live --output-dir outputs_live
python -m market_price_guard.main --provider-mode live --strict --output-dir outputs_live_strict
```

AKShare live 模式仅用于价格事实获取与数据完整度检查，不提供买卖建议。

## Provider Priority Chain

watchlist 支持为每个标的配置 `provider_priority`：

```yaml
provider_priority:
  - akshare
  - mock
```

旧配置中的 `provider` 字段仍然有效；如果没有 `provider_priority`，工具会使用单一 `provider`。live 模式会按优先级逐个尝试 provider，primary 失败但 fallback 成功时使用 fallback 结果，并在 `provider_health_report.md` 的 “Provider attempts by symbol” 中展示尝试链路。

`mock` fallback 仅用于开发和测试。live 模式下如果 AKShare 失败后选中 `mock` fallback，默认仍不可用于具体操作建议；只有标的显式配置 `allow_mock_fallback_for_operation: true` 时，才允许用于 strict 判断。

`00883.HK` 支持 yfinance secondary provider，内部映射为 Yahoo Finance ticker `0883.HK`。yfinance 是 Yahoo Finance public API wrapper，适合研究/教育用途，不是官方交易所行情源。

## Provider Policy

`--provider-policy` 支持 `fast`、`conservative`、`diagnostic`，默认 `fast`。

- `fast`：A股 / 港股股票优先 `yfinance -> akshare -> mock`，ETF 仍为 `akshare -> mock`，GOLD_CNY 仍为 `manual`。
- `conservative`：A股 / 港股股票优先 `akshare -> yfinance -> mock`，适合对比国内行情源与 yfinance。
- `diagnostic`：按配置链路运行并在报告中标注 diagnostic mode active，适合排查 provider 问题，可能慢于 fast。

常用命令：

```bash
python -m market_price_guard.main --profile energy --provider-mode live --provider-policy fast --strict --output-dir outputs_energy_latest
python -m market_price_guard.main --profile tech --provider-mode live --provider-policy fast --strict --output-dir outputs_tech_latest
python -m market_price_guard.main --profile all --provider-mode live --provider-policy fast --strict --output-dir outputs_all_latest
python -m market_price_guard.main --profile all --provider-mode live --provider-policy conservative --strict --output-dir outputs_conservative
python -m market_price_guard.main --profile all --provider-mode live --provider-policy diagnostic --output-dir outputs_diagnostic
```

## AKShare

live 模式下：

- A股股票使用 `ak.stock_zh_a_spot_em()`。
- 港股使用 `ak.stock_hk_spot_em()`。
- A股 ETF 使用 `ak.fund_etf_spot_em()`。

AKShare provider 支持分接口诊断和 fallback：

- A股总接口失败时，`.SH` 标的会尝试 `ak.stock_sh_a_spot_em()`，`.SZ` 标的会尝试 `ak.stock_sz_a_spot_em()`。
- 港股总接口失败时，会依次尝试 `ak.stock_hk_main_board_spot_em()` 和 `ak.stock_hsgt_sh_hk_spot_em()`。
- ETF 继续使用 `ak.fund_etf_spot_em()`，不受 A股 / 港股接口失败影响。
- strict 模式按每个 required 标的最终是否可用判断；主接口失败但 fallback 成功时，该标的不因主接口失败进入 blocking records。

ETF 的 `quote_time` 优先从 AKShare 返回的 `更新时间` 字段解析；如果无时区，按 Asia/Shanghai（UTC+08:00）处理并标记 `assumed_timezone_asia_shanghai`；如果只有 `数据日期`，标记 `quote_time_date_only` / `low_precision_quote_time`。

## GOLD_CNY 手工价

`GOLD_CNY` 来自 `config/manual_prices.yaml`，由 `manual_provider` 读取，不从 `config/mock_prices.yaml` 或 AKShare 获取。

`GOLD_CNY` 表示用户手工录入的黄金持仓参考价 / 估值价 / 可卖参考价，不等同于国际现货金价。它用于科技账户防守仓 / 潜在转科技资金的参考，实际操作前需核对账户内可卖价、手续费、点差和到账规则。

## Windows 中文报告查看

Markdown 报告使用 UTF-8 写入，CSV 使用 `utf-8-sig` 写入。PowerShell 查看中文报告时建议：

```powershell
chcp 65001
Get-Content outputs_mock\data_completeness_report.md -Encoding UTF8
```

也可以直接用 VS Code 打开报告文件。

## 科技账户分类

- `159632.SZ`、`513300.SH`：纳指 / 海外科技ETF。
- `159819.SZ`：AI / 人工智能ETF。
- `515880.SH`：通信 / 科技ETF。
- `510300.SH`：非科技宽基单独列示，不归入科技权益、AI、通信或纳指暴露。
- `GOLD_CNY`：黄金防守仓 / 潜在转科技资金，不归入科技权益。

## 指定配置运行

```bash
python -m market_price_guard.main \
  --watchlist config/watchlist.yaml \
  --stale-rules config/stale_rules.yaml \
  --mock-prices config/mock_prices.yaml \
  --manual-prices config/manual_prices.yaml \
  --provider-mode mock \
  --output-dir outputs
```

## strict 模式

strict 模式会把工具当作价格新鲜度守门员：只要 `required_for_operation=true` 的指标出现价格缺失、invalid_price、quote_time 缺失、quote_time 无效、provider 错误或 stale，就返回 exit code 2。

非 strict 模式不会因为 stale 或缺失而异常退出，只会生成报告。非 required 辅助指标 stale 只作为 warning 披露，不触发 strict exit code 2。

## Outputs

运行后生成：

- `outputs/prices_snapshot.csv`
- `outputs/data_completeness_report.md`
- `outputs/energy_price_block.md`
- `outputs/tech_price_block.md`
- `outputs/controller_price_summary.md`

## Test

```bash
pytest
```

日常开发默认测试（排除慢速和 live 网络类测试）：

```bash
pytest -m "not slow and not live"
```

快速验收默认使用 quick UAT：

```powershell
pytest
.\scripts\run_uat.ps1
```

UAT runtime profiles:

```powershell
.\scripts\run_uat.ps1 -Mode quick
.\scripts\run_uat.ps1 -Mode intraday
.\scripts\run_uat.ps1 -Mode full
```

`quick` 是默认模式，跳过 diagnostic / reconcile / scan_ai / energy / all 等重型 live provider 项；`intraday` 用于 minute probe / reference VWAP 开发验收；`full` 用于完整回归。详见 `docs/uat_profiles.md`。

可选 UAT run cache：

```powershell
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
.\scripts\run_uat.ps1 -Mode full -UseRunCache
```

`-UseRunCache` 默认关闭，只在当前 UAT run 内生效。v0.7.2c.1 第一版只缓存 `akshare.fund_etf_spot_em`，目录为 `outputs_uat_run_cache_latest`；不缓存 minute bars、YFinance、Eastmoney Direct、operation readiness、VWAP 或任何 advice 输出。cache hit 不改变 freshness、strict、quote_trust_tier、usable_for_operation 或 operation/reference 语义。详见 `docs/uat_run_cache.md`。

科技研究流水线：

```powershell
.\scripts\run_tech_research_pipeline.ps1
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache -SkipScan -SkipWatchlist
```

该脚本按 scan_ai、watchlist、operation_candidates、tech_fast_strict、minute_probe、intraday_metrics 的顺序生成科技研究链路输出，并写入 `outputs_tech_pipeline_latest/pipeline_summary.md` 与 `pipeline_manifest.json`。它只做 orchestration，不修改 config，不自动晋级标的，不改变 provider / strict / usable_for_operation，也不输出交易建议。

## 输出契约与 UAT

输出契约文档：

- `docs/output_contract.md`

UAT 检查清单：

- `docs/uat_checklist.md`
- `docs/uat_profiles.md`

运行快速 UAT：

```powershell
.\scripts\run_uat.ps1
```

运行完整 UAT：

```powershell
.\scripts\run_uat.ps1 -Mode full
```

查看 UAT 汇总：

```powershell
Get-Content outputs_uat_summary.md -Encoding UTF8
```

UAT 说明：

- strict=0：数据完整度通过，可进一步分析。
- strict=2：价格守门员阻断，不得用于具体操作建议。
- strict=2 不是 UAT 失败，前提是报告正确生成并说明阻断原因。
- skipped_by_profile 不是 UAT 失败，表示该 item 被当前 UAT mode 有意跳过。
- exit code=1 是程序错误，需要排查。
- UAT 主要验证输出契约、报告结构、阻断语义和项目接入稳定性。

输出契约变更规则：

- 如果未来修改 `index.md`、price block 或报告格式，必须同步更新 `docs/output_contract.md`、`docs/uat_checklist.md` 和 `tests/test_output_contract.py`。
- 科技账户项目已经 UAT pass，因此 `tech_price_block.md` 的分组名称和分类边界不得随意改变。

## v0.6.3 Quote Trust Tier Foundation

v0.6.3 只追加价格用途分层诊断字段，不改变现有一键脚本、provider-policy、strict 或 freshness 语义。

新增字段包括 `quote_trust_tier`、`usable_for_reference`、`quote_purpose`、`confirmation_required`、`operation_blocking_reason`、`reference_note`。当前 `quote_purpose` 默认仍为 `operation`，`run_tech_fast_strict.ps1` 和 `outputs_tech_latest` 的既有使用方式保持不变。

## Fast Reference Mode for Tech ETF

科技 ETF 快速参考：

```powershell
.\scripts\run_tech_fast_reference.ps1
```

输出目录：

- `outputs_tech_reference_latest`

该模式使用 `--quote-purpose reference`，用于快速查看科技 ETF 参考价；yfinance ETF 记录会标记为 `quote_trust_tier=reference`、`usable_for_operation=false`、`confirmation_required=true`。

该目录不可用于具体操作建议。如需具体操作确认，请继续使用：

```powershell
.\scripts\run_tech_fast_strict.ps1
```

## 最小上传口径

日常只需上传对应目录里的 `0_upload_bundle.md`：

- 科技 operation：`outputs_tech_latest/0_upload_bundle.md`
- 科技 reference：`outputs_tech_reference_latest/0_upload_bundle.md`
- 能源 operation：`outputs_energy_latest/0_upload_bundle.md`
- 总控摘要：`outputs_all_latest/0_upload_bundle.md`

异常时再补充同目录的 `debug_bundle.md`，例如 strict 阻断、provider 异常、运行超时、quote_time 可疑、价格 stale 或报告之间存在冲突。

科技 reference：

```powershell
.\scripts\run_tech_fast_reference.ps1
```

上传：

- `outputs_tech_reference_latest/0_upload_bundle.md`

用途：快速参考，不可用于具体操作价位。

科技 operation：

```powershell
.\scripts\run_tech_fast_strict.ps1
```

上传：

- `outputs_tech_latest/0_upload_bundle.md`

用途：operation / strict 输出，若通过可进入完整操作级分析。

Codex smoke test passed.

## Symbol Registry + Universe Layer

v0.7.1.2 adds `config/symbol_registry.yaml` and `config/universes/` so new watchlist or scan symbols can be added by configuration.

- `core_holdings`: core execution symbols; may affect operation strict when `required_for_operation=true`.
- `candidate_watchlist`: candidate symbols; default `required_for_operation=false`; does not pollute core strict.
- `scan_universe`: reference scan pools; never blocks core operation strict.

Example commands:

```powershell
.\scripts\run_tech_watchlist.ps1
.\scripts\run_tech_scan_ai.ps1
python -m market_price_guard.main --profile tech --symbols 512480.SH,159995.SZ --quote-purpose reference --output-dir outputs_temp_scan
```

Unknown symbols go to `unsupported_symbols_report.md` and remain non-strict reference records. See `docs/symbol_registry.md` for the registry fields and universe workflow.

## API Field Capability Matrix

The field capability audit is in `docs/api_field_capability_matrix.md`.

Read it as a provider/field support map:

- `supported`: currently standardized in models, CSV, reports, or runtime diagnostics.
- `partially_supported`: some provider or guard layer has pieces, but the field is not fully standardized.
- `provider_dependent`: provider capability needs validation or varies by endpoint.
- `missing`: not implemented.
- `planned`: future guard-derived or decision-layer field.

v0.7.1.3 does not develop the requested fields. It documents what exists now and what should move into later versions: v0.7.1.4 base quote field normalization, v0.7.1.5 provider capability expansion, v0.7.1.6 scan ranking, v0.7.2 advice-level gating, v0.7.3 minute bars/VWAP, and v0.7.4 QDII premium.

## Base Quote Field Normalization

v0.7.1.4 standardizes additive base quote fields when current providers already supply them:

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
- `exchange`
- `country_market`
- `trading_calendar`

These fields support future scan ranking, day-position diagnostics, liquidity checks, and advice-level gating. They do not change provider trust tier, freshness, strict, or operation/reference semantics. `price` remains the legacy primary price field, and `market` keeps its current meaning for freshness compatibility.

Use `prices_snapshot.csv` for the full normalized fields. `0_upload_bundle.md` includes a compact base quote summary, while `debug_bundle.md` includes field sources and missing-field diagnostics.

## Compact Base Quote Tables

v0.7.1.5 makes `0_upload_bundle.md` easier to use as the daily minimal upload file. Tech, energy, reference, watchlist, and scan bundles now include compact base quote tables with `last`, `open`, `high`, `low`, `prev`, `chg%`, `volume`, `amount`, and `base_quote_completeness` where available.

Use `debug_bundle.md` when you need field sources, missing fields, or provider capability notes. These notes are lightweight diagnostics, not a formal provider capability system. Field completeness does not mean operation-grade: operation use still depends on `quote_trust_tier`, `usable_for_operation`, strict, and freshness.

`volume` and `amount` remain provider raw units unless explicitly normalized. Do not use cross-provider volume/amount ranking until provider field validation is completed in a future version.

## Provider Capability / Field Validation

v0.7.1.6 adds a diagnostic capability layer:

- `config/provider_capabilities.yaml` records provider/function field support, units, operation/reference fit, and comparability flags.
- Each output directory now includes `provider_capability_report.md`.
- `prices_snapshot.csv` includes field quality, unit, and comparability columns such as `field_validation_status`, `volume_unit`, `amount_unit`, `volume_comparable_across_providers`, and `amount_comparable_across_providers`.
- `0_upload_bundle.md` keeps this compact through Field Quality Notes.
- `debug_bundle.md` links the full capability report and summarizes field-quality risks.

This version does not add providers, does not repair Eastmoney Direct, and does not change strict, freshness, provider chain, or operation/reference semantics. `volume` and `amount` remain unsafe for cross-provider ranking unless the relevant comparable flag is true. `bid/ask`, `turnover_rate`, `minute_bars`, VWAP, and QDII premium remain not validated or not implemented.

Watchlist and scan reports now distinguish candidate data coverage problems such as `provider_symbol_not_found` from system failure. These records remain `required_for_operation=false` and do not affect core strict.

## Scan Universe Basic Ranking

v0.7.1.7 adds conservative review-priority ranking for `candidate_watchlist` and `scan_universe` outputs.

New CSV/report fields include:

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

The score is a data-quality-first review priority:

`scan_score_basic = data_quality * 0.35 + momentum * 0.25 + field_reliability * 0.20 + liquidity * 0.10 + reconciliation * 0.10`

`rankable=false` means the current data is insufficient for basic ordering, for reasons such as `symbol_not_found`, `provider_error`, missing last price, missing quote time, development-only data, or missing base quote. It does not mean the symbol is permanently uninteresting.

`watch_priority=high/medium/low/not_rankable` is a review queue label only. It is not a trading instruction and does not change `strict`, `quote_trust_tier`, or `usable_for_operation`. `volume` and `amount` are not used to lift a candidate when comparability flags are false. Operation decisions still require operation-grade guard output.

## Tech Operation Candidates

v0.7.2a.2d adds an independent `tech_operation_candidates` universe for pre-trade verification candidates selected from scan or watchlist outputs.

Run it with:

```powershell
.\scripts\run_tech_operation_candidates.ps1
```

Output: `outputs_tech_operation_candidates_latest/`.

This layer is reference-only. It is not core holdings, is not operation-grade, does not affect `run_tech_fast_strict.ps1`, and does not affect `outputs_tech_latest`. The initial universe is intentionally empty; add symbols to `config/universes/tech_operation_candidates.yaml` only after manual selection. Candidate records keep `required_for_operation=false`, `usable_for_operation=false`, and `affect_core_strict=false`.

## Reference Intraday Metrics

v0.7.2b adds `run_tech_intraday_metrics.ps1` for reference VWAP and basic intraday position metrics based on the latest minute probe artifacts.

```powershell
.\scripts\run_tech_intraday_metrics.ps1
```

Output: `outputs_tech_intraday_latest/`.

The script reads `outputs_tech_minute_probe_latest/minute_bars_snapshot.csv`, tech core spot output, and tech operation-candidate spot output. It writes `intraday_metrics_snapshot.csv`, `reference_vwap_report.md`, `0_upload_bundle.md`, `debug_bundle.md`, and completeness diagnostics.

These metrics are reference-only. They do not change `strict`, `quote_trust_tier`, `usable_for_operation`, or operation/reference semantics. `reference_vwap` is not operation-grade and does not replace QDII premium / IOPV checks.

## Eastmoney Direct Provider

v0.7.0 新增 `eastmoney_direct`，用于 A股 ETF / A股股票的快速指定标的报价获取。它当前只作为 `reference` / `operation-candidate`：`quote_trust_tier=reference`、`usable_for_operation=false`、`confirmation_required=true`。

科技 reference 模式可优先使用 Eastmoney Direct；operation strict 路径仍保持原有放行标准。Eastmoney Direct 来源于东方财富公开网页行情接口路径，不是官方交易所实时行情源；后续 v0.7.1 计划增加多源价格差异检查后再评估是否提升信任等级。

## Multi-source Price Reconciliation

v0.7.1 新增 `price_reconciliation_report.md`，用于比较 `eastmoney_direct`、`akshare`、`yfinance` 等真实源的同标的价格差异。该报告只做数据质量诊断，不构成交易建议，也不会自动把 reference-grade 提升为 operation-grade。

如果出现 `major_diff`，请查看同目录的 `debug_bundle.md` 和 `price_reconciliation_report.md`。operation 输出仍必须以 strict、freshness、quote_trust_tier、usable_for_operation 等既有规则为准。

## Tech Reconcile Mode

v0.7.1.1 新增科技多源对账脚本：

```powershell
.\scripts\run_tech_reconcile.ps1
```

输出目录：`outputs_tech_reconcile_latest/`

该模式使用 `--reconcile-mode full`，尽量尝试 Eastmoney Direct、yfinance、AKShare，用于价格源质量诊断。它仍是 `quote_purpose=reference`，不可用于具体操作建议，也不会改变 operation strict。

当前链路说明见：`docs/current_provider_chains.md`。

日常上传优先使用 `0_upload_bundle.md`。如果出现 strict 阻断、provider_error、stale、quote_time_missing、major_diff、运行超时或报告冲突，再补充 `debug_bundle.md`。
## Minute Bars Ingestion Probe

v0.7.2a adds an optional minute-bars ingestion probe. It is diagnostic only and does not change strict, freshness, provider chain, quote trust tier, usable_for_operation, or operation/reference semantics.

Run the tech minute probe:

```powershell
.\scripts\run_tech_minute_probe.ps1
```

Output directory:

```text
outputs_tech_minute_probe_latest
```

The probe writes minute-bar availability fields into `prices_snapshot.csv` and adds Minute Bars Probe sections to `0_upload_bundle.md`, `debug_bundle.md`, `data_completeness_report.md`, and `provider_capability_report.md`. When mock mode is used, mock minute bars may be generated for tests only. Live providers that do not have a guarded minute-bars implementation are reported as `not_supported`, `not_validated`, or `not_implemented_for_provider`.

v0.7.2a does not calculate VWAP, intraday position fields, QDII premium, action hints, preferred actions, or allowed advice levels. Future v0.7.2b may build VWAP and basic intraday derived fields on top of this probe.

## AKShare Real Data Coverage for Scan + Minute Probe

v0.7.2a.1 expands AKShare real-data coverage in two diagnostic/reference paths:

- `run_tech_scan_ai.ps1` / `tech_scan_ai` now attempts AKShare spot quote coverage for scan ETF/QDII ETF candidates through `fund_etf_spot_em` and A-share scan stocks through stock spot helpers.
- `run_tech_minute_probe.ps1` now attempts AKShare ETF minute bars through `fund_etf_hist_min_em` when `--include-minute-bars` is enabled.

Scan records remain `required_for_operation=false` and `usable_for_operation=false`. Minute bars remain diagnostic and do not change strict, freshness, quote trust tier, operation readiness, or operation/reference semantics.

YFinance minute fallback is not implemented in this version; it remains reference-only/not implemented in guard capability reporting. Eastmoney Direct minute bars remain not validated.

## Eastmoney Direct Minute Probe

v0.7.2a.2 adds Eastmoney Direct as a diagnostic minute-bars fallback in the optional minute probe path. The probe order is AKShare first, then Eastmoney Direct when AKShare returns provider error, empty response, or unparseable bars.

Eastmoney Direct minute bars use Eastmoney `secid` mapping such as `513300.SH -> 1.513300` and `159632.SZ -> 0.159632`. Any successful Eastmoney minute bars remain reference/diagnostic only. They do not change strict, freshness, quote trust tier, usable_for_operation, or operation readiness. VWAP and intraday derived fields are still not calculated until a future version.

## YFinance Reference Minute Fallback

v0.7.2a.2b adds YFinance as the third optional minute-bars fallback after AKShare and Eastmoney Direct both fail to return usable bars. The fallback reuses the existing YFinance ticker mapping, records `yfinance_ticker` in diagnostics, and marks successful bars as `provider_dependent` / reference-only.

YFinance minute bars do not change strict, freshness, quote trust tier, usable_for_operation, or operation/reference semantics. VWAP and intraday derived fields are still not calculated.
