from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.script
def test_energy_research_pipeline_script_contract():
    script = Path("scripts/run_energy_research_pipeline.ps1").read_text(encoding="utf-8")

    for expected in [
        "run_energy_scan.ps1",
        "run_energy_watchlist.ps1",
        "run_energy_operation_candidates.ps1",
        "run_energy_fast_strict.ps1",
        "outputs_energy_pipeline_latest",
        "pipeline_summary.md",
        "pipeline_manifest.json",
        "pipeline_layer_manifest.json",
        "## Layer Config Summary",
        "## Data Completeness Summary",
        "## Runtime Diagnostics Summary",
        "no minute_probe",
        "no intraday_metrics",
        "no VWAP",
        "no trading advice",
    ]:
        assert expected in script
    assert "run_tech_minute_probe.ps1" not in script
    assert "run_tech_intraday_metrics.ps1" not in script
    assert "Set-Content config" not in script


@pytest.mark.script
def test_energy_uat_profile_declared():
    script = Path("scripts/run_uat.ps1").read_text(encoding="utf-8")

    for expected in [
        "'energy'",
        "energy_fast_strict",
        "energy_operation_candidates",
        "energy_watchlist",
        "energy_scan",
        "energy_pipeline",
        "run_energy_research_pipeline.ps1",
    ]:
        assert expected in script

