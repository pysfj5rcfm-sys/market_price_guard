from __future__ import annotations

from market_price_guard.providers.manual_provider import ManualProvider


def test_manual_provider_reads_gold_cny(tmp_path):
    manual_prices = tmp_path / "manual_prices.yaml"
    manual_prices.write_text(
        """
manual_prices:
  - symbol: "GOLD_CNY"
    name: "黄金持仓参考价"
    market: "MANUAL"
    price: 1040.0
    currency: "CNY"
    quote_time: "2026-05-18T09:30:00+08:00"
    source: "manual"
    source_note: "用户手工录入"
    product_type: "gold_savings_or_gold_wealth_product"
    price_type: "estimated_sellable_or_valuation_price"
    tradable: true
    fee_note: "手续费、点差、赎回到账规则未自动计算"
    project: "tech"
    asset_role: "defense_or_potential_tech_funding"
    is_core: true
    required_for_operation: true
""".strip(),
        encoding="utf-8",
    )

    prices = ManualProvider(manual_prices).fetch(["GOLD_CNY"])
    gold = prices["GOLD_CNY"]

    assert gold.source == "manual"
    assert gold.market == "MANUAL"
    assert gold.asset_role == "defense_or_potential_tech_funding"
    assert gold.required_for_operation is True
    assert gold.quality_issues == []
