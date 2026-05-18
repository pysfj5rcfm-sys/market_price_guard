# market_price_guard

价格实时获取与新鲜度校验工具，用于在理财项目之间共享价格事实、数据源、时间戳、市场状态和数据完整度提示。

本工具不提供买卖建议，不做自动交易，只做价格事实与数据完整度检查。第一版和第二阶段都不接真实外部行情源。

## Scope

- 能源账户：维护核心能源标的价格事实块。
- 科技账户：维护科技相关标的价格事实块；黄金作为防守/潜在转科技资金参考价单独标注。
- 总控项目：只输出摘要，不输出能源/科技账户完整明细。

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

默认输出到 `outputs/`。

## 指定配置运行

```bash
python -m market_price_guard.main \
  --watchlist config/watchlist.yaml \
  --stale-rules config/stale_rules.yaml \
  --mock-prices config/mock_prices.yaml \
  --output-dir outputs
```

## strict 模式

```bash
python -m market_price_guard.main --strict
```

strict 模式会把工具当作价格新鲜度守门员：只要核心标的或 `required_for_operation` 指标出现价格缺失、stale、或 `quote_time` 缺失导致无法证明新鲜，就返回 exit code 2。这样可以阻止上游流程继续把过期价格当成可操作信息，降低投资判断被旧数据污染的风险。

非 strict 模式不会因为 stale 或缺失而异常退出，只会生成报告，并在 `data_completeness_report.md` 中写明“不可用于具体操作建议”。

## Exit Codes

- `0`: 正常运行，报告已生成。
- `1`: 程序异常错误，例如配置文件无法读取或格式错误。
- `2`: strict 模式下，核心或必需价格数据缺失、stale、或缺少 `quote_time`。

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
- `manual_provider`: reads manually entered prices from `config/mock_prices.yaml`, including entry time.
- `akshare_provider`, `yfinance_provider`, `alphavantage_provider`: interface skeletons only and raise `NotImplementedError`.

Codex smoke test passed.
