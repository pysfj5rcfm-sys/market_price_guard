from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from market_price_guard.main import EXIT_OK, run_pipeline
from market_price_guard.models import RawPrice
from market_price_guard.normalize import load_watchlist, load_yaml, normalize_records
from market_price_guard.report import build_completeness_report, build_provider_health_report, build_tech_block


def test_prices_snapshot_keeps_old_columns_and_adds_quote_trust_columns(tmp_path):
    output_dir = tmp_path / "tech"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)
    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")

    old_columns = [
        "project",
        "symbol",
        "name",
        "source",
        "selected_provider",
        "price",
        "currency",
        "quote_time",
        "is_stale",
        "stale_reason",
        "usable_for_operation",
        "required_for_operation",
    ]
    new_columns = [
        "quote_trust_tier",
        "usable_for_reference",
        "quote_purpose",
        "confirmation_required",
        "operation_blocking_reason",
        "reference_note",
    ]

    for column in old_columns + new_columns:
        assert column in df.columns


def test_quote_trust_defaults_for_akshare_manual_mock_and_yfinance():
    records = _normalize(
        {
            "159819.SZ": _raw("159819.SZ", "akshare"),
            "GOLD_CNY": _raw("GOLD_CNY", "manual"),
            "00883.HK": _raw("00883.HK", "yfinance", currency="HKD"),
            "601899.SH": _raw("601899.SH", "mock"),
        }
    )
    by_symbol = {record.symbol: record for record in records}

    assert by_symbol["159819.SZ"].quote_trust_tier == "operation"
    assert by_symbol["159819.SZ"].usable_for_reference is True
    assert by_symbol["159819.SZ"].confirmation_required is False
    assert by_symbol["GOLD_CNY"].quote_trust_tier == "operation"
    assert by_symbol["601899.SH"].quote_trust_tier == "development"
    assert by_symbol["601899.SH"].usable_for_operation is False
    assert by_symbol["00883.HK"].quote_trust_tier == "reference"
    assert "Yahoo Finance" in by_symbol["00883.HK"].reference_note


def test_invalid_record_is_not_reference_or_operation_grade():
    records = _normalize({"159819.SZ": _raw("159819.SZ", "akshare", price=None, quote_time=None, issues=["quote_time_missing"])})
    record = next(item for item in records if item.symbol == "159819.SZ")

    assert record.quote_trust_tier == "development"
    assert record.usable_for_reference is False
    assert record.usable_for_operation is False
    assert record.confirmation_required is True


def test_yfinance_etf_is_reference_only_if_ever_called():
    records = _normalize({"159819.SZ": _raw("159819.SZ", "yfinance")})
    record = next(item for item in records if item.symbol == "159819.SZ")

    assert record.quote_trust_tier == "reference"
    assert record.usable_for_reference is True
    assert record.usable_for_operation is False
    assert record.confirmation_required is True
    assert record.operation_blocking_reason == "reference_tier_requires_operation_confirmation"


def test_reports_include_quote_trust_sections(tmp_path):
    output_dir = tmp_path / "tech"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)

    index = (output_dir / "index.md").read_text(encoding="utf-8")
    completeness = (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")
    tech_block = (output_dir / "tech_price_block.md").read_text(encoding="utf-8")
    provider_health = (output_dir / "provider_health_report.md").read_text(encoding="utf-8")
    runtime = (output_dir / "runtime_diagnostics.md").read_text(encoding="utf-8")

    assert "Quote trust summary" in index
    assert "可用于具体操作建议" in index
    assert "Quote trust tier diagnostics" in completeness
    assert "quote_trust_tier" in tech_block
    assert "quote_trust_tier" in provider_health
    assert "quote_purpose" in runtime


def test_tech_flow_and_scoped_outputs_remain_backward_compatible(tmp_path):
    output_dir = tmp_path / "tech"

    result = run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)

    assert result.exit_code == EXIT_OK
    assert (output_dir / "tech_price_block.md").exists()
    assert not (output_dir / "energy_price_block.md").exists()
    assert not (output_dir / "controller_price_summary.md").exists()


def test_report_builders_expose_quote_trust_without_changing_sections():
    records = _normalize({"159819.SZ": _raw("159819.SZ", "akshare")})

    assert "Quote trust tier diagnostics" in build_completeness_report(records)
    assert "quote_trust_tier" in build_provider_health_report(records, provider_mode="live")
    assert "quote_trust_tier" in build_tech_block(records)


def _normalize(raw_prices: dict[str, RawPrice]):
    watchlist = load_watchlist(Path("config/watchlist.yaml"))
    rules = load_yaml(Path("config/stale_rules.yaml"))
    return normalize_records(watchlist, raw_prices, rules, now=datetime(2026, 5, 18, 16, 10, tzinfo=timezone.utc))


def _raw(
    symbol: str,
    source: str,
    *,
    price: float | None = 1.23,
    currency: str = "CNY",
    quote_time: datetime | None = datetime(2026, 5, 18, 15, 10, tzinfo=timezone.utc),
    issues: list[str] | None = None,
) -> RawPrice:
    return RawPrice(
        symbol=symbol,
        source=source,
        price=price,
        currency=currency,
        name=symbol,
        quote_time=quote_time,
        fetch_time=datetime(2026, 5, 18, 16, 10, tzinfo=timezone.utc),
        market_status="closed",
        quality_issues=issues or [],
        provider_diagnostics={"selected_provider": source, "usable_for_operation": True},
    )
