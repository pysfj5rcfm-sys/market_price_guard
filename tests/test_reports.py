from datetime import datetime, timezone

from market_price_guard.models import PriceRecord
from market_price_guard.report import build_completeness_report, build_controller_summary, records_to_dataframe


def make_record(project: str = "energy", stale: bool = False) -> PriceRecord:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    return PriceRecord(
        project=project,
        symbol="00883.HK",
        name="中海油H",
        market="HK",
        price=21.35,
        currency="HKD",
        source="mock",
        quote_time=now,
        fetch_time=now,
        market_status="closed",
        is_stale=stale,
        stale_reason="收盘/最后成交参考价，不可用于盘中做T" if not stale else "不可用于具体操作建议",
        core=True,
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


def test_completeness_report_blocks_specific_advice_when_stale():
    report = build_completeness_report([make_record(stale=True)])

    assert "不可用于具体操作建议" in report


def test_controller_summary_is_summary_only():
    report = build_controller_summary([make_record("energy"), make_record("tech"), make_record("controller")])

    assert "只维护摘要同步块" in report
    assert "00883.HK" not in report
