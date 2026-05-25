from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from market_price_guard.main import run_pipeline
from market_price_guard.models import PriceRecord
from market_price_guard.scan_ranking import rank_record


NOW = datetime(2026, 5, 20, 7, 0, tzinfo=timezone.utc)


def test_scan_ranking_scores_and_exclusions():
    complete = _record(base_quote_completeness="complete", field_validation_status="validated")
    partial = _record(base_quote_completeness="partial", field_validation_status="provider_raw")
    missing = _record(base_quote_completeness="missing")
    symbol_not_found = _record(quality_issues=["symbol_not_found"])
    provider_error = _record(quality_issues=["provider_error"])
    development = _record(quote_trust_tier="development", source="mock", selected_provider="mock")

    assert rank_record(complete)["data_quality_score"] == 100
    assert rank_record(partial)["data_quality_score"] == 70
    assert rank_record(missing)["rankable"] is False
    assert rank_record(symbol_not_found)["rank_exclusion_reason"] == "symbol_not_found"
    assert rank_record(provider_error)["rank_exclusion_reason"] == "provider_error"
    assert rank_record(development)["rank_exclusion_reason"] == "development_only"


def test_scan_ranking_conservative_momentum_liquidity_and_reconciliation():
    high_move = _record(price_change_pct=6.2)
    raw_liquidity = _record(amount=100000000, amount_comparable_across_providers=False)
    major_diff = _record(source_agreement_status="major_diff")
    single_source = _record(source_agreement_status="single_source_only")

    high_move_rank = rank_record(high_move)
    raw_liquidity_rank = rank_record(raw_liquidity)
    major_diff_rank = rank_record(major_diff)
    single_source_rank = rank_record(single_source)

    assert high_move_rank["momentum_score_basic"] == 60
    assert "high_move_needs_intraday_confirmation" in str(high_move_rank["scan_score_notes"])
    assert raw_liquidity_rank["liquidity_score_basic"] == 50
    assert "amount_not_comparable" in str(raw_liquidity_rank["scan_score_notes"])
    assert major_diff_rank["watch_priority"] == "low"
    assert single_source_rank["reconciliation_score"] == 55


def test_scan_reports_upload_debug_csv_and_completeness_include_ranking(tmp_path):
    scan_dir = tmp_path / "scan"
    watchlist_dir = tmp_path / "watchlist"
    run_pipeline(output_dir=scan_dir, provider_mode="mock", profile="tech", universe="tech_scan_ai", quote_purpose="reference")
    run_pipeline(output_dir=watchlist_dir, provider_mode="mock", profile="tech", universe="tech_watchlist", quote_purpose="reference")

    scan_report = (scan_dir / "scan_universe_report.md").read_text(encoding="utf-8")
    watchlist_report = (watchlist_dir / "candidate_watchlist_report.md").read_text(encoding="utf-8")
    upload = (scan_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    debug = (scan_dir / "debug_bundle.md").read_text(encoding="utf-8")
    completeness = (scan_dir / "data_completeness_report.md").read_text(encoding="utf-8")
    snapshot = pd.read_csv(scan_dir / "prices_snapshot.csv", encoding="utf-8-sig")

    assert "Scan Universe Basic Ranking" in scan_report
    assert "Basic Ranking Table" in scan_report
    assert "Not Rankable" in scan_report
    assert "not operation guidance" in scan_report
    assert "Watchlist Review Priority" in watchlist_report
    assert "Scan Priority Summary" in upload
    assert "Top Scan Candidates" in upload
    assert "Scan Ranking Trace" in debug
    assert "Scan Ranking Summary" in completeness
    for column in ["rankable", "scan_score_basic", "watch_priority", "rank_exclusion_reason", "scan_score_notes"]:
        assert column in snapshot.columns


def test_scan_ranking_docs_are_updated():
    readme = Path("README.md").read_text(encoding="utf-8")
    output_contract = Path("docs/output_contract.md").read_text(encoding="utf-8")
    matrix = Path("docs/api_field_capability_matrix.md").read_text(encoding="utf-8")
    known_issues = Path("docs/known_issues.md").read_text(encoding="utf-8")

    assert "Scan Universe Basic Ranking" in readme
    assert "Scan Ranking Contract" in output_contract
    assert "v0.7.1.7 Scan Universe Basic Ranking Update" in matrix
    assert "Scan Ranking Limits" in known_issues


def _record(**overrides) -> PriceRecord:
    data = {
        "project": "tech",
        "symbol": "159819.SZ",
        "name": "AI ETF",
        "market": "CN",
        "price": 10.0,
        "last_price": 10.0,
        "prev_close": 9.8,
        "open_price": 9.9,
        "high_price": 10.2,
        "low_price": 9.7,
        "volume": 1000,
        "amount": 10000,
        "price_change_pct": 2.0,
        "currency": "CNY",
        "source": "akshare",
        "selected_provider": "akshare",
        "quote_time": NOW,
        "fetch_time": NOW,
        "market_status": "open",
        "is_stale": False,
        "required_for_operation": False,
        "quote_trust_tier": "reference",
        "usable_for_reference": True,
        "usable_for_operation": False,
        "confirmation_required": True,
        "base_quote_completeness": "complete",
        "field_validation_status": "provider_raw",
        "volume_comparable_across_providers": False,
        "amount_comparable_across_providers": False,
        "volume_unit_confidence": "low",
        "amount_unit_confidence": "low",
        "source_agreement_status": "single_source_only",
        "universe_type": "scan_universe",
    }
    data.update(overrides)
    return PriceRecord(**data)
