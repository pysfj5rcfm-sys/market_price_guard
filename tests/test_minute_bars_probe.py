from __future__ import annotations

from pathlib import Path

import pandas as pd

from market_price_guard.main import parse_args, run_pipeline
from market_price_guard.models import PriceRecord


MINUTE_COLUMNS = [
    "minute_bars_available",
    "minute_bar_provider",
    "minute_bar_interval",
    "minute_bar_count",
    "minute_bar_latest_time",
    "minute_bar_fetch_time",
    "minute_bar_status",
    "minute_bar_validation_status",
    "minute_bar_missing_reason",
    "minute_bar_notes",
]


def test_price_record_contains_minute_bar_probe_fields():
    fields = PriceRecord.model_fields
    for column in MINUTE_COLUMNS:
        assert column in fields


def test_cli_accepts_include_minute_bars_aliases():
    assert parse_args(["--include-minute-bars"]).include_minute_bars is True
    assert parse_args(["--minute-bars-probe"]).include_minute_bars is True


def test_minute_probe_outputs_reports_and_csv_columns(tmp_path):
    output_dir = tmp_path / "minute_probe"
    result = run_pipeline(
        output_dir=output_dir,
        provider_mode="mock",
        profile="tech",
        quote_purpose="reference",
        include_minute_bars=True,
    )

    assert result.exit_code == 0
    snapshot = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")
    for column in MINUTE_COLUMNS:
        assert column in snapshot.columns

    assert (output_dir / "minute_bars_snapshot.csv").exists()
    assert "Minute Bars Probe Summary" in (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    assert "Minute Bars Probe Detail" in (output_dir / "debug_bundle.md").read_text(encoding="utf-8")
    assert "Minute Bars Completeness" in (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")
    assert "Minute Bars Capability" in (output_dir / "provider_capability_report.md").read_text(encoding="utf-8")


def test_minute_probe_disabled_preserves_strict_result(tmp_path):
    without_probe = run_pipeline(output_dir=tmp_path / "without", provider_mode="mock", profile="tech", strict=True)
    with_probe = run_pipeline(
        output_dir=tmp_path / "with",
        provider_mode="mock",
        profile="tech",
        strict=True,
        include_minute_bars=True,
    )

    assert without_probe.exit_code == with_probe.exit_code
    assert not (tmp_path / "without" / "minute_bars_snapshot.csv").exists()
    assert (tmp_path / "with" / "minute_bars_snapshot.csv").exists()


def test_manual_gold_minute_bars_are_not_supported(tmp_path):
    output_dir = tmp_path / "gold"
    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", include_minute_bars=True)
    snapshot = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")
    gold = snapshot[snapshot["symbol"] == "GOLD_CNY"].iloc[0]

    assert gold["minute_bar_status"] == "not_supported"
    assert gold["minute_bar_missing_reason"] == "manual_price_only"


def test_minute_probe_script_and_docs_are_present():
    script = Path("scripts/run_tech_minute_probe.ps1").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    output_contract = Path("docs/output_contract.md").read_text(encoding="utf-8")
    matrix = Path("docs/api_field_capability_matrix.md").read_text(encoding="utf-8")
    known_issues = Path("docs/known_issues.md").read_text(encoding="utf-8")

    assert "--include-minute-bars" in script
    assert "outputs_tech_minute_probe_latest" in script
    assert "Minute Bars Ingestion Probe" in readme
    assert "Minute Bars Probe Contract" in output_contract
    assert "v0.7.2a probe introduced" in matrix
    assert "Minute bars probe introduced in v0.7.2a" in known_issues
