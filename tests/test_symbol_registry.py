from __future__ import annotations

from pathlib import Path

import pytest

from market_price_guard.main import CONFIG_DIR, run_pipeline
from market_price_guard.symbol_registry import build_watchlist_from_registry, load_symbol_registry, load_universe


REGISTRY_PATH = CONFIG_DIR / "symbol_registry.yaml"
UNIVERSES_DIR = CONFIG_DIR / "universes"


@pytest.mark.unit
def test_symbol_registry_contains_core_and_candidate_metadata():
    registry = load_symbol_registry(REGISTRY_PATH)

    for symbol in ["159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH", "GOLD_CNY"]:
        assert symbol in registry
    for symbol in ["00883.HK", "601899.SH", "601985.SH", "003816.SZ"]:
        assert symbol in registry

    assert registry["510300.SH"]["role"] == "non_tech_broad_base_etf"
    assert registry["512480.SH"]["required_for_operation"] is False


@pytest.mark.unit
@pytest.mark.parametrize("name", ["tech_core", "tech_watchlist", "tech_scan_ai", "tech_operation_candidates", "energy_core", "controller_core"])
def test_universe_files_load(name):
    spec = load_universe(name, UNIVERSES_DIR)

    assert spec.name == name
    if name == "tech_operation_candidates":
        assert spec.universe_type == "operation_candidate"
    else:
        assert spec.symbols


@pytest.mark.unit
def test_watchlist_universe_candidate_symbols_are_not_required_for_operation():
    watchlist, metadata = build_watchlist_from_registry(
        REGISTRY_PATH,
        UNIVERSES_DIR,
        profile="tech",
        quote_purpose="reference",
        universe="tech_watchlist",
    )

    instruments = watchlist.projects["tech"].instruments
    assert metadata["universe_type"] == "candidate_watchlist"
    assert all(item.required_for_operation is False for item in instruments)
    assert all(item.universe_type == "candidate_watchlist" for item in instruments)


@pytest.mark.unit
def test_scan_universe_symbols_are_reference_and_not_required_for_operation():
    watchlist, metadata = build_watchlist_from_registry(
        REGISTRY_PATH,
        UNIVERSES_DIR,
        profile="tech",
        quote_purpose="reference",
        universe="tech_scan_ai",
    )

    instruments = watchlist.projects["tech"].instruments
    assert metadata["universe_type"] == "scan_universe"
    assert all(item.required_for_operation is False for item in instruments)
    assert all(item.default_quote_purpose == "reference" for item in instruments)


@pytest.mark.unit
def test_operation_candidate_universe_is_non_strict():
    watchlist, metadata = build_watchlist_from_registry(
        REGISTRY_PATH,
        UNIVERSES_DIR,
        profile="tech",
        quote_purpose="reference",
        universe="tech_operation_candidates",
    )

    assert metadata["universe_type"] == "operation_candidate"
    instruments = watchlist.projects.get("tech").instruments if "tech" in watchlist.projects else []
    assert metadata["operation_candidate_count"] == len(instruments)
    assert all(item.required_for_operation is False for item in instruments)
    assert all(item.affect_core_strict is False for item in instruments)
    assert all(item.operation_candidate is True for item in instruments)


@pytest.mark.unit
def test_operation_candidate_cli_symbols_are_reference_only():
    watchlist, metadata = build_watchlist_from_registry(
        REGISTRY_PATH,
        UNIVERSES_DIR,
        profile="tech",
        quote_purpose="reference",
        symbols="159819.SZ",
        universe_type="operation_candidate",
    )

    instrument = watchlist.projects["tech"].instruments[0]
    assert metadata["universe_type"] == "operation_candidate"
    assert instrument.operation_candidate is True
    assert instrument.required_for_operation is False
    assert instrument.affect_core_strict is False
    assert instrument.default_quote_purpose == "reference"


@pytest.mark.unit
def test_symbols_cli_priority_over_universe_and_unknown_is_scan_only():
    watchlist, metadata = build_watchlist_from_registry(
        REGISTRY_PATH,
        UNIVERSES_DIR,
        profile="tech",
        quote_purpose="reference",
        universe="tech_core",
        symbols="512480.SH,UNKNOWN_BAD",
    )

    instruments = watchlist.projects["tech"].instruments
    assert [item.symbol for item in instruments] == ["512480.SH", "UNKNOWN_BAD"]
    unknown = next(item for item in instruments if item.symbol == "UNKNOWN_BAD")
    assert unknown.required_for_operation is False
    assert unknown.universe_type == "scan_universe"
    assert unknown.registry_found is False
    assert metadata["unsupported_count"] == 1


@pytest.mark.unit
def test_symbol_file_loads_temporary_symbols(tmp_path):
    symbol_file = tmp_path / "symbols.txt"
    symbol_file.write_text("512480.SH\n159995.SZ\n", encoding="utf-8")

    watchlist, metadata = build_watchlist_from_registry(
        REGISTRY_PATH,
        UNIVERSES_DIR,
        profile="tech",
        quote_purpose="reference",
        symbol_file=symbol_file,
    )

    assert [item.symbol for item in watchlist.projects["tech"].instruments] == ["512480.SH", "159995.SZ"]
    assert metadata["universe_name"] == "symbols"


@pytest.mark.contract
def test_scan_universe_strict_isolation_and_reports(tmp_path):
    output_dir = tmp_path / "scan"

    result = run_pipeline(
        output_dir=output_dir,
        provider_mode="mock",
        strict=True,
        profile="tech",
        quote_purpose="reference",
        universe="tech_scan_ai",
    )

    assert result.exit_code == 0
    assert (output_dir / "scan_universe_report.md").exists()
    assert not (output_dir / "tech_price_block.md").exists()
    upload = (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    assert "universe_name: tech_scan_ai" in upload
    assert "universe_type: scan_universe" in upload
    assert "core strict pollution isolation" in upload
    assert "not usable for concrete operation recommendations" in upload


@pytest.mark.contract
def test_unsupported_symbols_report_generated_for_unknown_symbol(tmp_path):
    output_dir = tmp_path / "unsupported"

    result = run_pipeline(
        output_dir=output_dir,
        provider_mode="mock",
        strict=True,
        profile="tech",
        quote_purpose="reference",
        symbols="UNKNOWN_BAD",
    )

    assert result.exit_code == 0
    report = (output_dir / "unsupported_symbols_report.md").read_text(encoding="utf-8")
    assert "UNKNOWN_BAD" in report
    assert "suggested_fix" in report


@pytest.mark.contract
def test_operation_candidates_universe_outputs(tmp_path):
    output_dir = tmp_path / "operation_candidates"

    result = run_pipeline(
        output_dir=output_dir,
        provider_mode="mock",
        profile="tech",
        quote_purpose="reference",
        universe="tech_operation_candidates",
    )

    assert result.exit_code == 0
    assert (output_dir / "operation_candidate_report.md").exists()
    assert not (output_dir / "tech_price_block.md").exists()
    upload = (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    debug = (output_dir / "debug_bundle.md").read_text(encoding="utf-8")
    report = (output_dir / "operation_candidate_report.md").read_text(encoding="utf-8")
    assert "Operation Candidate Summary" in upload
    assert "not usable for concrete operation recommendations" in upload
    assert "operation_candidate_count:" in debug
    assert "not core holdings" in report


@pytest.mark.contract
def test_operation_candidate_symbols_do_not_become_operation(tmp_path):
    output_dir = tmp_path / "operation_candidates_symbol"

    result = run_pipeline(
        output_dir=output_dir,
        provider_mode="mock",
        profile="tech",
        quote_purpose="reference",
        symbols="159819.SZ",
        universe_type="operation_candidate",
    )

    assert result.exit_code == 0
    import pandas as pd

    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")
    row = df[df["symbol"] == "159819.SZ"].iloc[0]
    assert row["operation_candidate"] == True
    assert row["required_for_operation"] == False
    assert row["affect_core_strict"] == False
    assert row["usable_for_operation"] == False
    assert row["universe_type"] == "operation_candidate"
    assert row["candidate_data_status"] in {"ready_for_review", "data_incomplete"}


@pytest.mark.script
def test_watchlist_and_scan_scripts_are_reference_only():
    scripts = {
        "run_tech_watchlist.ps1": ("--universe tech_watchlist", "outputs_tech_watchlist_latest"),
        "run_tech_scan_ai.ps1": ("--universe tech_scan_ai", "outputs_tech_scan_ai_latest"),
        "run_tech_operation_candidates.ps1": ("--universe tech_operation_candidates", "outputs_tech_operation_candidates_latest"),
    }
    for script, (universe_arg, output_dir) in scripts.items():
        content = (Path("scripts") / script).read_text(encoding="utf-8")
        assert universe_arg in content
        assert output_dir in content
        assert "--provider-mode live" in content
        assert "--quote-purpose reference" in content
        assert "--strict" not in content


@pytest.mark.contract
def test_default_tech_profile_merges_registry_metadata(tmp_path):
    output_dir = tmp_path / "tech_default"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)

    import pandas as pd

    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")
    ai = df[df["symbol"] == "159819.SZ"].iloc[0]
    communication = df[df["symbol"] == "515880.SH"].iloc[0]
    broad = df[df["symbol"] == "510300.SH"].iloc[0]

    assert ai["asset_type"] == "ETF"
    assert ai["project_scope"] == "tech"
    assert ai["role"] == "ai_tech_equity"
    assert ai["report_group"] == "AI / 人工智能ETF"
    assert communication["report_group"] == "通信 / 科技ETF"
    assert broad["role"] == "non_tech_broad_base_etf"


@pytest.mark.contract
def test_default_energy_profile_merges_registry_metadata(tmp_path):
    output_dir = tmp_path / "energy_default"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="energy", strict=True)

    import pandas as pd

    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")
    zijin = df[df["symbol"] == "601899.SH"].iloc[0]
    cgn = df[df["symbol"] == "003816.SZ"].iloc[0]

    assert zijin["asset_type"] == "stock"
    assert zijin["project_scope"] == "energy"
    assert zijin["role"] == "energy_core_equity"
    assert zijin["report_group"] == "能源账户核心价格"
    assert cgn["asset_type"] == "stock"


@pytest.mark.contract
def test_explicit_universe_metadata_still_complete(tmp_path):
    output_dir = tmp_path / "scan_default"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", quote_purpose="reference", universe="tech_scan_ai")

    import pandas as pd

    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")
    ai = df[df["symbol"] == "159819.SZ"].iloc[0]

    assert ai["asset_type"] == "ETF"
    assert ai["report_group"] == "AI / 人工智能ETF"
    assert ai["role"] == "ai_tech_equity"
    assert ai["universe_type"] == "scan_universe"
