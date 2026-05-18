# market_price_guard

价格实时获取与新鲜度校验工具，用于在理财项目之间共享价格事实、数据源、时间戳、市场状态和数据完整度提示。

第一版不接真实外部行情源，不做自动交易，不输出买卖建议。

## Scope

- 能源账户：维护核心能源标的价格事实块。
- 科技账户：维护科技相关标的价格事实块；黄金作为防守/潜在转科技资金参考价单独标注。
- 总控项目：只输出摘要，不输出能源/科技账户完整明细。

## Install

```bash
pip install -e ".[dev]"
```

## Run

```bash
python -m market_price_guard.main
```

The command generates:

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
- `akshare_provider`, `yfinance_provider`, `alphavantage_provider`: first-version interface skeletons only.

Codex smoke test passed.
