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

## 输出契约与 UAT

输出契约文档：

- `docs/output_contract.md`

UAT 检查清单：

- `docs/uat_checklist.md`

运行完整 UAT：

```powershell
.\scripts\run_uat.ps1
```

查看 UAT 汇总：

```powershell
Get-Content outputs_uat_summary.md -Encoding UTF8
```

UAT 说明：

- strict=0：数据完整度通过，可进一步分析。
- strict=2：价格守门员阻断，不得用于具体操作建议。
- strict=2 不是 UAT 失败，前提是报告正确生成并说明阻断原因。
- exit code=1 是程序错误，需要排查。
- UAT 主要验证输出契约、报告结构、阻断语义和项目接入稳定性。

输出契约变更规则：

- 如果未来修改 `index.md`、price block 或报告格式，必须同步更新 `docs/output_contract.md`、`docs/uat_checklist.md` 和 `tests/test_output_contract.py`。
- 科技账户项目已经 UAT pass，因此 `tech_price_block.md` 的分组名称和分类边界不得随意改变。

Codex smoke test passed.
