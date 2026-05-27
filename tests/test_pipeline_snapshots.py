from __future__ import annotations

import re
from pathlib import Path


TECH_BASELINE = {
    "tech_core": 7,
    "tech_operation_candidates": 19,
    "tech_watchlist": 28,
    "tech_scan_ai": 40,
}
ENERGY_BASELINE = {
    "energy_core": 4,
    "energy_operation_candidates": 8,
    "energy_watchlist": 24,
    "energy_scan": 41,
}


def _script(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_current_account_baselines_are_declared_in_tests_and_config_check():
    assert TECH_BASELINE == {
        "tech_core": 7,
        "tech_operation_candidates": 19,
        "tech_watchlist": 28,
        "tech_scan_ai": 40,
    }
    assert ENERGY_BASELINE == {
        "energy_core": 4,
        "energy_operation_candidates": 8,
        "energy_watchlist": 24,
        "energy_scan": 41,
    }


def test_old_tech_baseline_is_not_a_current_assertion():
    current_assertion_files = [
        Path("tests/test_account_layers.py"),
        Path("tests/test_manage_tech_layers.py"),
        Path("docs/HANDOFF_v0.7.5.1.md"),
    ]

    for path in current_assertion_files:
        text = path.read_text(encoding="utf-8")
        assert "operation_candidate: `11`" not in text
        assert "watchlist: `16`" not in text
        assert "scan: `30`" not in text
        assert '"operation_candidate": 11' not in text
        assert '"watchlist": 16' not in text
        assert '"scan": 30' not in text


def test_tech_pipeline_snapshot_contract():
    script = _script("scripts/run_tech_research_pipeline.ps1")

    for expected in [
        "$PipelineRunId",
        "$SnapshotRoot",
        "Copy-PipelineStepSnapshot",
        "outputs_tech_pipeline_latest",
        "'tech_scan_ai'",
        "'tech_watchlist'",
        "'tech_operation_candidates'",
        "'tech_fast_strict'",
        "'tech_minute_probe'",
        "'tech_intraday_metrics'",
        "snapshot_metadata.json",
        "layer_manifest.json",
        "data_completeness_report.md",
        "runtime_diagnostics.md",
        "provider_health_report.md",
        "0_upload_bundle.md",
        "prices_snapshot.csv",
        "layer_manifest_hash_sha256",
        "prices_snapshot_hash_sha256",
        "upload_bundle_hash_sha256",
        "pipeline_layer_manifest.json",
        "snapshot_steps",
        "## Pipeline Output Snapshots",
    ]:
        assert expected in script
    assert "snapshots are copied during this pipeline run" in script


def test_energy_pipeline_snapshot_contract_excludes_intraday_steps():
    script = _script("scripts/run_energy_research_pipeline.ps1")

    for expected in [
        "$PipelineRunId",
        "$SnapshotRoot",
        "Copy-PipelineStepSnapshot",
        "outputs_energy_pipeline_latest",
        "'energy_scan'",
        "'energy_watchlist'",
        "'energy_operation_candidates'",
        "'energy_fast_strict'",
        "snapshot_metadata.json",
        "layer_manifest.json",
        "data_completeness_report.md",
        "runtime_diagnostics.md",
        "provider_health_report.md",
        "0_upload_bundle.md",
        "prices_snapshot.csv",
        "layer_manifest_hash_sha256",
        "prices_snapshot_hash_sha256",
        "upload_bundle_hash_sha256",
        "pipeline_layer_manifest.json",
        "snapshot_steps",
        "## Pipeline Output Snapshots",
    ]:
        assert expected in script
    assert "run_tech_minute_probe.ps1" not in script
    assert "run_tech_intraday_metrics.ps1" not in script
    assert "reference_vwap_report.md" not in script


def test_pipeline_summary_and_manifest_reference_snapshot_paths():
    for script_path in [
        "scripts/run_tech_research_pipeline.ps1",
        "scripts/run_energy_research_pipeline.ps1",
    ]:
        script = _script(script_path)
        assert "snapshot_dir" in script
        assert "snapshot_metadata_path" in script
        assert "step_snapshot_dir" in script
        assert "layer_manifest_path" in script
        assert "source_run_id" in script
        assert "generated_at" in script
        assert re.search(r"snapshot_steps\s*=\s*@\(\$SnapshotEntries\)", script)


def test_uat_summaries_remain_mode_specific():
    script = _script("scripts/run_uat.ps1")

    assert "$ModeSummaryDir = Join-Path $SummaryRoot $Mode" in script
    assert "$SummaryPath = Join-Path $ModeSummaryDir 'outputs_uat_summary.md'" in script
    assert "uat_run_manifest.json" in script
    for mode in ["quick", "intraday", "energy"]:
        assert mode in script
