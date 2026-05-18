from datetime import datetime, timezone

from market_price_guard.models import PriceRecord
from market_price_guard.report import (
    build_completeness_report,
    build_controller_summary,
    build_tech_block,
    get_blocking_records,
    records_to_dataframe,
)


def make_record(
    project: str = "energy",
    stale: bool = False,
    price: float | None = 21.35,
    quote_time: datetime | None = None,
    required_for_operation: bool = False,
) -> PriceRecord:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    return PriceRecord(
        project=project,
        symbol="00883.HK",
        name="中海油H",
        market="HK",
        price=price,
        currency="HKD",
        source="mock",
        quote_time=now if quote_time is None else quote_time,
        fetch_time=now,
        market_status="closed",
        is_stale=stale,
        stale_reason="收盘/最后成交参考价，不可用于盘中做T" if not stale else "不可用于具体操作建议",
        core=True,
        required_for_operation=required_for_operation,
    )


def test_dataframe_contains_required_columns():
    df = records_to_dataframe([make_record()])

    assert list(df.columns) == [
        "project",
        "symbol",
        "name",
        "market",
        "price",
        "currency",
        "source",
        "quote_time",
        "fetch_time",
        "market_status",
        "is_stale",
        "stale_reason",
    ]


def test_completeness_report_blocks_specific_advice_when_required_stale():
    report = build_completeness_report([make_record(stale=True, required_for_operation=True)])

    assert "可用于具体操作建议：否" in report
    assert "不可用于具体操作建议" in report
    assert "Strict blocking records" in report


def test_completeness_report_lists_quote_time_missing():
    record = make_record(stale=True, quote_time=None, required_for_operation=True)
    record.quote_time = None
    report = build_completeness_report([record])

    assert "quote_time_missing" in report


def test_controller_summary_is_summary_only():
    report = build_controller_summary([make_record("energy"), make_record("tech"), make_record("controller")])

    assert "只维护摘要同步块" in report
    assert "00883.HK" not in report


def test_gold_is_not_reported_as_tech_equity():
    tech_equity = make_record("tech")
    tech_equity.symbol = "513300.SH"
    tech_equity.name = "纳指ETF"
    tech_equity.asset_role = "tech_equity"
    gold = make_record("tech")
    gold.symbol = "GOLD_CNY"
    gold.name = "黄金持仓参考价"
    gold.source = "manual"
    gold.asset_role = "defense_or_potential_tech_funding"

    report = build_tech_block([tech_equity, gold])
    tech_equity_section = report.split("## 黄金防守仓 / 潜在转科技资金")[0]

    assert "GOLD_CNY" not in tech_equity_section
    assert "黄金防守仓 / 潜在转科技资金" in report


def test_get_blocking_records_requires_required_for_operation():
    required = make_record(stale=True, required_for_operation=True)
    optional = make_record(project="controller", stale=True, required_for_operation=False)

    blocking = get_blocking_records([required, optional])

    assert [record["symbol"] for record in blocking] == ["00883.HK"]
    assert blocking[0]["blocking_reason"] == "stale"
