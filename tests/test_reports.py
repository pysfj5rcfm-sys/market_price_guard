from datetime import datetime, timezone

from market_price_guard.models import PriceRecord
from market_price_guard.report import (
    build_completeness_report,
    build_controller_summary,
    build_provider_health_report,
    build_tech_block,
    get_blocking_records,
    records_to_dataframe,
)


def make_record(
    project: str = "energy",
    symbol: str = "00883.HK",
    name: str = "中海油H",
    stale: bool = False,
    price: float | None = 21.35,
    quote_time: datetime | None = None,
    required_for_operation: bool = False,
    asset_role: str | None = None,
) -> PriceRecord:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    return PriceRecord(
        project=project,
        symbol=symbol,
        name=name,
        market="HK" if symbol.endswith(".HK") else "CN",
        price=price,
        currency="HKD" if symbol.endswith(".HK") else "CNY",
        source="mock",
        quote_time=now if quote_time is None else quote_time,
        fetch_time=now,
        market_status="closed",
        is_stale=stale,
        stale_reason="收盘/最后成交参考价，不可用于盘中做T" if not stale else "不可用于具体操作建议",
        core=True,
        required_for_operation=required_for_operation,
        asset_role=asset_role,
    )


def test_dataframe_contains_required_columns():
    df = records_to_dataframe([make_record()])

    old_columns = [
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
    new_columns = [
        "selected_provider",
        "usable_for_operation",
        "required_for_operation",
        "quote_trust_tier",
        "usable_for_reference",
        "quote_purpose",
        "confirmation_required",
        "operation_blocking_reason",
        "reference_note",
    ]

    for column in old_columns + new_columns:
        assert column in df.columns


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


def test_completeness_report_references_provider_health_report():
    report = build_completeness_report([make_record()])

    assert "provider_health_report.md" in report


def test_provider_health_report_includes_manual_gold():
    record = make_record(
        "tech",
        "GOLD_CNY",
        "黄金持仓参考价",
        asset_role="defense_or_potential_tech_funding",
    )
    record.source = "manual"
    record.market = "MANUAL"
    record.source_note = "用户手工录入"

    report = build_provider_health_report([record])

    assert "## Manual" in report
    assert "GOLD_CNY" in report
    assert "用户手工录入" in report


def test_controller_summary_is_summary_only():
    report = build_controller_summary([make_record("energy"), make_record("tech"), make_record("controller")])

    assert "只维护摘要同步块" in report
    assert "00883.HK" not in report


def test_tech_block_groups_assets_without_mixing():
    records = [
        make_record("tech", "159632.SZ", "纳指相关ETF", asset_role="nasdaq_or_overseas_tech_etf"),
        make_record("tech", "513300.SH", "纳指ETF", asset_role="nasdaq_or_overseas_tech_etf"),
        make_record("tech", "159819.SZ", "人工智能ETF", asset_role="ai_tech_equity"),
        make_record("tech", "515880.SH", "通信ETF", asset_role="communication_tech_equity"),
        make_record("tech", "510300.SH", "沪深300ETF", asset_role="non_tech_broad_base_etf"),
        make_record("tech", "GOLD_CNY", "黄金持仓参考价", asset_role="defense_or_potential_tech_funding"),
    ]

    report = build_tech_block(records)
    nasdaq = _section(report, "纳指 / 海外科技ETF", "AI / 人工智能ETF")
    ai = _section(report, "AI / 人工智能ETF", "通信 / 科技ETF")
    communication = _section(report, "通信 / 科技ETF", "黄金防守仓 / 潜在转科技资金")
    gold = _section(report, "黄金防守仓 / 潜在转科技资金", "非科技宽基单独列示")
    broad = report.split("## 非科技宽基单独列示", 1)[1]

    assert "159632.SZ" in nasdaq and "513300.SH" in nasdaq
    assert "159819.SZ" in ai
    assert "515880.SH" in communication
    assert "GOLD_CNY" in gold
    assert "510300.SH" in broad
    assert "510300.SH" not in nasdaq + ai + communication
    assert "GOLD_CNY" not in nasdaq + ai + communication


def test_get_blocking_records_requires_required_for_operation():
    required = make_record(stale=True, required_for_operation=True)
    optional = make_record(project="controller", stale=True, required_for_operation=False)

    blocking = get_blocking_records([required, optional])

    assert [record["symbol"] for record in blocking] == ["00883.HK"]
    assert blocking[0]["blocking_reason"] == "stale"


def _section(report: str, start: str, end: str) -> str:
    return report.split(f"## {start}", 1)[1].split(f"## {end}", 1)[0]
