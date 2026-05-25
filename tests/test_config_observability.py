from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from market_price_guard.config_observability import (
    extract_configured_symbols,
    layer_manifest_summary_lines,
    load_target_layer_manifest,
    run_config_check,
)
from market_price_guard.main import run_pipeline


@pytest.mark.unit
def test_layer_manifest_extracts_top_level_symbols_only():
    data = {
        "symbols": ["AAA.SZ", "BBB.SH"],
        "forbidden": [{"symbol": "NOPE.SZ"}],
        "deleted_by_this_update": [{"symbol": "OLD.SH"}],
        "notes": {"symbol": "NOTE.SZ"},
        "layers": {"nested": {"symbols": ["NESTED.SZ"]}},
    }

    assert extract_configured_symbols(data) == ["AAA.SZ", "BBB.SH"]


@pytest.mark.unit
def test_layer_manifest_detects_loaded_mismatch():
    manifest = load_target_layer_manifest("tech_operation_candidates", ["159819.SZ"])

    assert manifest["configured_symbol_count"] == 11
    assert manifest["loaded_symbol_count"] == 1
    assert manifest["config_mismatch"] is True
    assert "515880.SH" in manifest["missing_from_loaded"]
    assert "CONFIG_MISMATCH: true" in "\n".join(layer_manifest_summary_lines(manifest))


@pytest.mark.contract
def test_current_tech_layer_manifest_counts():
    assert load_target_layer_manifest("tech_operation_candidates", [])["configured_symbol_count"] == 11
    assert load_target_layer_manifest("tech_watchlist", [])["configured_symbol_count"] == 16
    assert load_target_layer_manifest("tech_scan_ai", [])["configured_symbol_count"] == 30


@pytest.mark.contract
def test_config_check_root_mirror_and_registry(tmp_path):
    result = run_config_check(tmp_path)

    assert (tmp_path / "tech_layer_config_check.md").exists()
    assert (tmp_path / "tech_layer_config_check.json").exists()
    assert result["universes"]["tech_core"]["configured_symbol_count"] == 7
    assert result["universes"]["tech_operation_candidates"]["root_mirror_matches"] is True
    assert result["universes"]["tech_watchlist"]["root_mirror_matches"] is True
    assert result["universes"]["tech_scan_ai"]["root_mirror_matches"] is True
    assert result["missing_registry_symbols"] == []


@pytest.mark.contract
def test_run_pipeline_writes_layer_manifest_and_reports(tmp_path):
    output_dir = tmp_path / "operation_candidates"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", quote_purpose="reference", universe="tech_operation_candidates")

    manifest = json.loads((output_dir / "layer_manifest.json").read_text(encoding="utf-8"))
    assert manifest["configured_symbol_count"] == 11
    assert manifest["loaded_symbol_count"] == 11
    assert manifest["config_mismatch"] is False
    assert "Config Source / Layer Manifest" in (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    assert "Config Source / Layer Manifest" in (output_dir / "debug_bundle.md").read_text(encoding="utf-8")
    assert "Config Source / Layer Manifest" in (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")
    assert "Config Source / Layer Manifest" in (output_dir / "runtime_diagnostics.md").read_text(encoding="utf-8")


@pytest.mark.contract
def test_strict_and_usable_for_operation_unchanged_by_manifest(tmp_path):
    output_dir = tmp_path / "tech"

    result = run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)
    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")

    assert result.exit_code in {0, 2}
    assert set(df["required_for_operation"].astype(str).str.lower()) <= {"true", "false"}
    assert "affect_core_strict" in df.columns
    assert (output_dir / "layer_manifest.json").exists()


@pytest.mark.script
def test_check_tech_layer_config_script_declared():
    script = Path("scripts/check_tech_layer_config.ps1").read_text(encoding="utf-8")

    assert "market_price_guard.check_tech_layer_config" in script
    assert "outputs_config_check_latest" in script


@pytest.mark.script
def test_pipeline_summary_declares_layer_config_summary():
    script = Path("scripts/run_tech_research_pipeline.ps1").read_text(encoding="utf-8")

    assert "## Layer Config Summary" in script
    assert "pipeline_layer_manifest.json" in script
    assert "CONFIG_MISMATCH: true" in script
