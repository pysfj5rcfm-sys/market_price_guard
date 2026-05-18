# market_price_guard

价格实时获取与新鲜度校验工具，用于在理财项目之间共享价格事实、数据源、时间戳、市场状态和数据完整度提示。

本工具不提供买卖建议，不做自动交易，只做价格事实与数据完整度检查。当前版本不接真实 AKShare、yfinance 或 Alpha Vantage 行情源。

## Scope

- 能源账户：维护核心能源标的价格事实块。
- 科技账户：维护科技相关标的价格事实块；黄金是防守仓 / 潜在转科技资金来源，不是科技资产本身。
- 总控项目：只输出摘要，不输出能源/科技账户完整明细。

## GOLD_CNY 手工价

`GOLD_CNY` 来自 `config/manual_prices.yaml`，由 `manual_provider` 读取，不从 `config/mock_prices.yaml` 获取。

`GOLD_CNY` 表示用户手工录入的黄金持仓参考价 / 估值价 / 可卖参考价，不等同于国际现货金价。它用于科技账户防守仓 / 潜在转科技资金的参考，实际操作前需核对账户内可卖价、手续费、点差和到账规则。

## Install

```bash
pip install -e ".[dev]"
```

## 默认运行

```bash
python -m market_price_guard.main
```

默认读取：

- `config/watchlist.yaml`
- `config/stale_rules.yaml`
- `config/mock_prices.yaml`
- `config/manual_prices.yaml`

默认输出到 `outputs/`。

## 指定配置运行

```bash
python -m market_price_guard.main \
  --watchlist config/watchlist.yaml \
  --stale-rules config/stale_rules.yaml \
  --mock-prices config/mock_prices.yaml \
  --manual-prices config/manual_prices.yaml \
  --output-dir outputs
```

## strict 模式

```bash
python -m market_price_guard.main --strict
```

strict 模式会把工具当作价格新鲜度守门员：只要 `required_for_operation=true` 的指标出现价格缺失、invalid_price、quote_time 缺失、quote_time 无效、provider 错误或 stale，就返回 exit code 2。`GOLD_CNY` 是科技账户 required 手工价，因此 stale、缺失或无效时 strict 模式也会返回 exit code 2。

非 strict 模式不会因为 stale 或缺失而异常退出，只会生成报告，并在 `data_completeness_report.md` 中写明“不可用于具体操作建议”。非 required 辅助指标 stale 只作为 warning 披露，不触发 strict exit code 2。

## strict 故障排查

当 strict 返回 exit code 2 时，控制台会打印：

```text
Strict mode blocked operation because the following required prices are not usable:
```

随后列出每条 blocking record 的 `project`、`symbol`、`name`、`source`、`quote_time`、`is_stale`、`stale_reason` 和 `blocking_reason`。同样的信息也会写入 `outputs/data_completeness_report.md` 的 `Strict blocking records` 小节。

如果你刚更新了 `GOLD_CNY quote_time` 但 strict 仍失败，优先查看 blocking records。常见原因包括其它 `required_for_operation=true` 标的 stale、`quote_time` 缺失或无效、价格缺失或 `invalid_price`。

## Exit Codes

- `0`: 正常运行，报告已生成。
- `1`: 程序异常错误，例如配置文件无法读取或格式错误。
- `2`: strict 模式下，required 价格数据缺失、stale、缺少或无效 `quote_time`、invalid_price 或 provider 错误。

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

## Providers

- `mock_provider`: reads example prices from `config/mock_prices.yaml`.
- `manual_provider`: reads manually entered prices from `config/manual_prices.yaml`, including `GOLD_CNY`.
- `akshare_provider`, `yfinance_provider`, `alphavantage_provider`: interface skeletons only and raise `NotImplementedError`.

Codex smoke test passed.
