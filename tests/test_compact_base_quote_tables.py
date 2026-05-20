from __future__ import annotations

from pathlib import Path

from market_price_guard.main import run_pipeline


def test_tech_upload_bundle_contains_compact_base_quote_snapshot(tmp_path):
    output_dir = tmp_path / "tech"
    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)
    bundle = (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")

    assert "基础行情快照 / Base Quote Snapshot" in bundle
    for expected in ["last", "chg%", "open", "high", "low", "prev", "volume", "amount", "base"]:
        assert expected in bundle
    assert "volume/amount follow provider raw units" in bundle
    assert "base_quote_completeness" in bundle or "| base |" in bundle


def test_reference_and_scan_upload_bundles_keep_reference_boundary(tmp_path):
    reference_dir = tmp_path / "reference"
    scan_dir = tmp_path / "scan"
    run_pipeline(output_dir=reference_dir, provider_mode="mock", profile="tech", quote_purpose="reference")
    run_pipeline(output_dir=scan_dir, provider_mode="mock", profile="tech", universe="tech_scan_ai", quote_purpose="reference")

    reference_bundle = (reference_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    scan_bundle = (scan_dir / "0_upload_bundle.md").read_text(encoding="utf-8")

    assert "基础行情快照 / Base Quote Snapshot" in reference_bundle
    assert "不可用于具体操作建议" in reference_bundle
    assert "scan_only" in scan_bundle or "symbol_not_found" in scan_bundle or "missing" in scan_bundle
    assert "not usable for concrete operation recommendations" in scan_bundle


def test_controller_upload_bundle_uses_summary_not_full_execution_table(tmp_path):
    output_dir = tmp_path / "all"
    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="all", strict=True)
    bundle = (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")

    assert "基础行情摘要 / Base Quote Summary" in bundle
    assert "| scope | complete | partial | price_only | missing | note |" in bundle
    assert "| symbol | name | last | chg% | open | high | low | prev | volume | amount |" not in bundle


def test_price_blocks_append_base_quote_fields(tmp_path):
    tech_dir = tmp_path / "tech"
    energy_dir = tmp_path / "energy"
    run_pipeline(output_dir=tech_dir, provider_mode="mock", profile="tech", strict=True)
    run_pipeline(output_dir=energy_dir, provider_mode="mock", profile="energy", strict=True)

    tech_block = (tech_dir / "tech_price_block.md").read_text(encoding="utf-8")
    energy_block = (energy_dir / "energy_price_block.md").read_text(encoding="utf-8")

    for content in [tech_block, energy_block]:
        assert "基础行情字段 / Base Quote Fields" in content
        assert "missing_fields" in content
        assert "volume/amount follow provider raw units" in content


def test_watchlist_and_scan_reports_have_compact_base_quote_tables(tmp_path):
    watchlist_dir = tmp_path / "watchlist"
    scan_dir = tmp_path / "scan"
    run_pipeline(output_dir=watchlist_dir, provider_mode="mock", profile="tech", universe="tech_watchlist", quote_purpose="reference")
    run_pipeline(output_dir=scan_dir, provider_mode="mock", profile="tech", universe="tech_scan_ai", quote_purpose="reference")

    watchlist = (watchlist_dir / "candidate_watchlist_report.md").read_text(encoding="utf-8")
    scan = (scan_dir / "scan_universe_report.md").read_text(encoding="utf-8")

    assert "Compact Base Quote Table" in watchlist
    assert "required_for_operation" in watchlist
    assert "Compact Base Quote Table" in scan
    assert "data_status" in scan
    assert "opportunity_rank" not in scan


def test_debug_and_completeness_include_capability_notes_and_caveats(tmp_path):
    output_dir = tmp_path / "tech"
    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)

    debug = (output_dir / "debug_bundle.md").read_text(encoding="utf-8")
    completeness = (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")

    assert "Base Quote Field Sources" in debug
    assert "Provider Capability Notes" in debug
    assert "AKShare:" in debug
    assert "Eastmoney Direct:" in debug
    assert "base_quote_completeness counts" in completeness
    assert "volume/amount follow provider raw units" in completeness
    assert "base quote missing does not change existing strict" in completeness


def test_compact_base_quote_docs_are_updated():
    readme = Path("README.md").read_text(encoding="utf-8")
    output_contract = Path("docs/output_contract.md").read_text(encoding="utf-8")
    matrix = Path("docs/api_field_capability_matrix.md").read_text(encoding="utf-8")
    known_issues = Path("docs/known_issues.md").read_text(encoding="utf-8")

    assert "Compact Base Quote Tables" in readme
    assert "Compact Base Quote Table Contract" in output_contract
    assert "v0.7.1.5 improves presentation" in matrix
    assert "Provider Capability Expansion / Field Validation" in known_issues
