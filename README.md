# market_price_guard

价格实时获取与新鲜度校验工具，用于在理财项目之间共享价格事实、数据源、时间戳、市场状态和数据完整度提示。

本工具不提供买卖建议，不做自动交易，只做价格事实与数据完整度检查。不做仓位市值计算。

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

Codex smoke test passed.
