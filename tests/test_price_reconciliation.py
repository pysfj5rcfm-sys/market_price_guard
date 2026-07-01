from __future__ import annotations

from datetime import datetime, timedelta, timezone

from market_price_guard.models import PriceRecord
from market_price_guard.main import parse_args, run_pipeline
from market_price_guard.price_reconciliation import apply_reconciliation, build_reconciliation_report
from market_price_guard.providers.akshare_provider import AkshareProvider
from market_price_guard.providers.eastmoney_direct_provider import EastmoneyDirectProvider
from market_price_guard.providers.yfinance_provider import YFinanceProvider
from market_price_guard.report import build_debug_bundle, build_upload_bundle


BASE_TIME = datetime(2026, 5, 19, 6, 55, tzinfo=timezone.utc)


def test_reconciliation_aligned_when_prices_equal():
    record = _record("159819.SZ", "eastmoney_direct", 1.000, [_source("yfinance", 1.000)])

    apply_reconciliation([record])

    assert record.source_agreement_status == "aligned"
    assert record.price_diff_pct == 0
    assert record.operation_candidate_agreed is True


def test_etf_reconciliation_thresholds():
    cases = [
        (1.0014, "aligned"),
        (1.0025, "minor_diff"),
        (1.0060, "warning_diff"),
        (1.0100, "major_diff"),
    ]
    for candidate_price, expected in cases:
        record = _record("159819.SZ", "eastmoney_direct", 1.000, [_source("yfinance", candidate_price)])
        apply_reconciliation([record])

        assert record.source_agreement_status == expected


def test_a_share_reconciliation_thresholds():
    cases = [
        (10.020, "aligned"),
        (10.040, "minor_diff"),
        (10.080, "warning_diff"),
        (10.200, "major_diff"),
    ]
    for candidate_price, expected in cases:
        record = _record("601899.SH", "eastmoney_direct", 10.000, [_source("yfinance", candidate_price)])
        apply_reconciliation([record])

        assert record.source_agreement_status == expected


def test_single_source_and_insufficient_data_statuses():
    single = _record("159819.SZ", "eastmoney_direct", 1.000, [])
    empty = _record("159819.SZ", "eastmoney_direct", None, [_source("yfinance", None, issues=["quote_time_missing"])])

    apply_reconciliation([single, empty])

    assert single.source_agreement_status == "single_source_only"
    assert empty.source_agreement_status in {"provider_error", "insufficient_data"}


def test_provider_error_source_does_not_participate_in_diff():
    record = _record("159819.SZ", "eastmoney_direct", 1.000, [_source("yfinance", None, issues=["provider_error"])])

    apply_reconciliation([record])

    assert record.source_agreement_status == "single_source_only"
    assert record.compared_sources == "eastmoney_direct"


def test_quote_time_gap_seconds_calculated():
    record = _record("159819.SZ", "eastmoney_direct", 1.000, [_source("yfinance", 1.000, quote_time=BASE_TIME + timedelta(seconds=450))])

    apply_reconciliation([record])

    assert record.quote_time_gap_seconds == 450
    assert "time_gap_warning" in record.reconciliation_note


def test_reconciliation_report_and_bundles_include_diagnostics(tmp_path):
    record = _record("159819.SZ", "eastmoney_direct", 1.000, [_source("yfinance", 1.010)])
    apply_reconciliation([record])

    report = build_reconciliation_report([record], {"profile": "tech", "provider_mode": "live", "provider_policy": "fast", "quote_purpose": "reference"})
    upload = build_upload_bundle([record], tmp_path, provider_mode="live", runtime={"profile": "tech", "quote_purpose": "reference"})
    debug = build_debug_bundle([record], tmp_path, provider_mode="live", runtime={"profile": "tech", "quote_purpose": "reference"})

    assert "source_agreement_status" in report
    assert "price_diff_pct" in report
    assert "quote_time_gap_seconds" in report
    assert "does not automatically upgrade reference-grade" in report
    assert "major_diff" in upload
    assert "Price Reconciliation" in debug


def test_reconciliation_does_not_change_operation_usability():
    record = _record("159819.SZ", "eastmoney_direct", 1.000, [_source("yfinance", 1.000)])
    record.quote_trust_tier = "reference"
    record.usable_for_operation = False

    apply_reconciliation([record])

    assert record.operation_candidate_agreed is True
    assert record.quote_trust_tier == "reference"
    assert record.usable_for_operation is False


def test_reconcile_mode_cli_accepts_default_and_full():
    assert parse_args([]).reconcile_mode == "default"
    assert parse_args(["--reconcile-mode", "full"]).reconcile_mode == "full"


def test_full_reconcile_mode_attempts_multiple_sources_for_tech_etf(monkeypatch, tmp_path):
    calls = {"eastmoney": [], "yfinance": [], "akshare": []}

    def eastmoney_fetch(self, symbols):
        calls["eastmoney"].extend(symbols)
        return {symbol: _raw_price(symbol, "eastmoney_direct", 1.000) for symbol in symbols if symbol in {"159819.SZ"}}

    def yfinance_fetch(self, symbols):
        calls["yfinance"].extend(symbols)
        return {symbol: _raw_price(symbol, "yfinance", 1.001) for symbol in symbols if symbol in {"159819.SZ"}}

    def akshare_fetch(self, symbols):
        calls["akshare"].extend(symbols)
        return {symbol: _raw_price(symbol, "akshare", 1.002) for symbol in symbols if symbol in {"159819.SZ"}}

    monkeypatch.setattr(EastmoneyDirectProvider, "fetch", eastmoney_fetch)
    monkeypatch.setattr(YFinanceProvider, "fetch", yfinance_fetch)
    monkeypatch.setattr(AkshareProvider, "fetch", akshare_fetch)

    output_dir = tmp_path / "reconcile"
    run_pipeline(
        output_dir=output_dir,
        provider_mode="live",
        provider_policy="diagnostic",
        profile="tech",
        quote_purpose="reference",
        reconcile_mode="full",
    )
    report = (output_dir / "price_reconciliation_report.md").read_text(encoding="utf-8")
    upload = (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")

    assert "159819.SZ" in calls["eastmoney"]
    assert "159819.SZ" not in calls["yfinance"]
    assert "reconcile_mode: full" in upload
    assert "159819.SZ" in report
    assert "single_source_only" in _line_for_symbol(report, "159819.SZ")
    assert not (output_dir / "energy_price_block.md").exists()
    assert not (output_dir / "controller_price_summary.md").exists()


def _raw_price(symbol: str, source: str, price: float):
    from market_price_guard.models import RawPrice

    return RawPrice(
        symbol=symbol,
        name=symbol,
        market="CN",
        price=price,
        currency="CNY",
        source=source,
        quote_time=BASE_TIME,
        fetch_time=BASE_TIME,
        market_status="open",
        provider_diagnostics={"provider": source, "function_name": f"{source}.mock"},
        quote_trust_tier="reference" if source == "eastmoney_direct" else None,
        confirmation_required=True if source == "eastmoney_direct" else None,
        operation_blocking_reason="reference_tier_requires_operation_confirmation" if source == "eastmoney_direct" else "",
    )


def _line_for_symbol(report: str, symbol: str) -> str:
    return next(line for line in report.splitlines() if line.startswith(f"| {symbol} |"))


def _record(symbol: str, source: str, price: float | None, reconciliation_sources: list[dict[str, object]]) -> PriceRecord:
    return PriceRecord(
        project="tech",
        symbol=symbol,
        name=symbol,
        market="CN",
        price=price,
        currency="CNY",
        source=source,
        quote_time=BASE_TIME if price is not None else None,
        fetch_time=BASE_TIME,
        market_status="open",
        is_stale=False,
        required_for_operation=True,
        selected_provider=source,
        provider_diagnostics={"selected_provider": source, "reconciliation_sources": reconciliation_sources},
        quote_trust_tier="reference" if source == "eastmoney_direct" else "operation",
        usable_for_reference=price is not None,
        usable_for_operation=source != "eastmoney_direct" and price is not None,
        confirmation_required=source == "eastmoney_direct",
        operation_blocking_reason="reference_tier_requires_operation_confirmation" if source == "eastmoney_direct" else "",
        asset_role="ai_tech_equity",
    )


def _source(source: str, price: float | None, quote_time: datetime | None = BASE_TIME, issues: list[str] | None = None) -> dict[str, object]:
    return {
        "source": source,
        "status": "success" if price is not None and not issues else "failed",
        "price": "" if price is None else price,
        "quote_time": quote_time.isoformat() if quote_time else "",
        "quality_issues": issues or [],
    }
