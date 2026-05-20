from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from market_price_guard.main import run_pipeline


def test_provider_capabilities_config_documents_units_and_gaps():
    config = yaml.safe_load(Path("config/provider_capabilities.yaml").read_text(encoding="utf-8"))

    for provider in ["akshare", "eastmoney_direct", "yfinance", "manual", "mock"]:
        assert provider in config

    akshare_fields = config["akshare"]["fund_etf_spot_em"]["fields"]
    yfinance_fields = config["yfinance"]["ticker_quote"]["fields"]

    assert akshare_fields["volume"]["comparable_across_providers"] is False
    assert akshare_fields["amount"]["comparable_across_providers"] is False
    assert yfinance_fields["volume"]["comparable_across_providers"] is False
    assert akshare_fields["bid1_price"]["status"] in {"not_validated", "missing", "not_supported"}
    assert akshare_fields["minute_bars"]["status"] == "not_implemented"
    assert akshare_fields["premium_pct"]["status"] in {"missing", "not_implemented"}


def test_provider_capability_report_and_csv_fields_are_generated(tmp_path):
    output_dir = tmp_path / "tech"
    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)

    report = (output_dir / "provider_capability_report.md").read_text(encoding="utf-8")
    debug = (output_dir / "debug_bundle.md").read_text(encoding="utf-8")
    bundle = (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    completeness = (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")
    snapshot = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")

    assert "Provider Capability Summary" in report
    assert "Field Capability Matrix By Provider" in report
    assert "Symbol Field Quality" in report
    assert "diagnostic only" in report
    assert "This report is not trading advice" in report
    assert "Provider Capability Summary" in debug
    assert "provider_capability_report.md" in debug
    assert "Field Quality Notes" in bundle
    assert "cross-provider volume/amount comparison is unsafe" in bundle
    assert "Field Quality / Provider Capability" in completeness
    assert "field validation issues do not change existing strict" in completeness

    for column in [
        "field_validation_status",
        "volume_unit",
        "amount_unit",
        "volume_comparable_across_providers",
        "amount_comparable_across_providers",
        "provider_capability_status",
        "provider_capability_notes",
        "last_price",
        "base_quote_completeness",
    ]:
        assert column in snapshot.columns


def test_watchlist_and_scan_reports_explain_symbol_not_found_without_failing(tmp_path):
    watchlist_dir = tmp_path / "watchlist"
    scan_dir = tmp_path / "scan"

    watchlist_result = run_pipeline(
        output_dir=watchlist_dir,
        provider_mode="mock",
        profile="tech",
        universe="tech_watchlist",
        quote_purpose="reference",
    )
    scan_result = run_pipeline(
        output_dir=scan_dir,
        provider_mode="mock",
        profile="tech",
        universe="tech_scan_ai",
        quote_purpose="reference",
    )

    watchlist = (watchlist_dir / "candidate_watchlist_report.md").read_text(encoding="utf-8")
    scan = (scan_dir / "scan_universe_report.md").read_text(encoding="utf-8")

    assert watchlist_result.exit_code == 0
    assert scan_result.exit_code == 0
    assert "Provider Coverage / Failure Reasons" in watchlist
    assert "Provider Coverage / Failure Reasons" in scan
    assert "provider_symbol_not_found" in watchlist or "symbol_not_found" in watchlist
    assert "provider_symbol_not_found" in scan or "symbol_not_found" in scan
    assert "required_for_operation=false" in watchlist or "do not affect core operation strict" in watchlist
    assert "does not affect core strict" in scan


def test_provider_capability_docs_are_updated():
    readme = Path("README.md").read_text(encoding="utf-8")
    output_contract = Path("docs/output_contract.md").read_text(encoding="utf-8")
    matrix = Path("docs/api_field_capability_matrix.md").read_text(encoding="utf-8")
    known_issues = Path("docs/known_issues.md").read_text(encoding="utf-8")

    assert "Provider Capability / Field Validation" in readme
    assert "Provider Capability Report Contract" in output_contract
    assert "v0.7.1.6 Provider Capability / Field Validation Update" in matrix
    assert "Provider Capability Expansion / Field Validation delivered" in known_issues
