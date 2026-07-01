from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
import yaml

from market_price_guard import config_observability
from market_price_guard import main as main_module
from market_price_guard.config_observability import (
    build_layer_manifest,
    extract_configured_symbols,
    layer_manifest_summary_lines,
    load_target_layer_manifest,
    run_config_check,
)
from market_price_guard.main import run_pipeline


def _configured_count(layer_name: str) -> int:
    data = yaml.safe_load(Path(f"config/universes/{layer_name}.yaml").read_text(encoding="utf-8"))
    return len(data["symbols"])


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

    assert manifest["configured_symbol_count"] == 19
    assert manifest["loaded_symbol_count"] == 1
    assert manifest["config_mismatch"] is True
    assert "515880.SH" in manifest["missing_from_loaded"]
    assert manifest["filtered_symbols"]
    assert {item["filter_reason"] for item in manifest["filtered_symbols"]} == {"configured_symbol_not_loaded"}
    assert "CONFIG_MISMATCH: true" in "\n".join(layer_manifest_summary_lines(manifest))


@pytest.mark.unit
def test_operation_manifest_separates_loaded_from_current_positions(monkeypatch, tmp_path):
    operation_symbols = [f"000{i:03d}.SZ" for i in range(1, 26)]
    current_positions = operation_symbols[:20]
    validators = operation_symbols[20:]
    config_path = tmp_path / "config" / "universes" / "tech_core.yaml"
    watchlist_path = tmp_path / "config" / "watchlist.yaml"
    config_path.parent.mkdir(parents=True)
    _write_yaml(
        config_path,
        {
            "name": "tech_core",
            "profile": "tech",
            "universe_type": "core_holdings",
            "quote_purpose": "operation",
            "symbols": operation_symbols,
        },
    )
    _write_yaml(
        watchlist_path,
        {
            "projects": {
                "tech": {
                    "display_name": "tech",
                    "allow_full_detail": True,
                    "instruments": [{"symbol": symbol, "name": symbol, "market": "CN"} for symbol in current_positions],
                    "layer_universes": {"operation": operation_symbols},
                }
            }
        },
    )
    monkeypatch.setattr(config_observability, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(config_observability, "WATCHLIST_PATH", watchlist_path)

    manifest = build_layer_manifest(
        layer_name="tech_core",
        universe_name="tech_core",
        universe_type="core_holdings",
        config_source_path=config_path,
        configured_symbols=operation_symbols,
        loaded_symbols=operation_symbols,
        strict_required_symbols=operation_symbols[:7],
        root_watchlist_layer_name="operation",
    )

    assert manifest["configured_symbol_count"] == 25
    assert manifest["loaded_symbol_count"] == 25
    assert manifest["current_position_symbol_count"] == 20
    assert manifest["current_position_symbols"] == current_positions
    assert manifest["operation_validator_symbols"] == validators
    assert manifest["strict_required_symbols"] == operation_symbols[:7]
    assert manifest["loaded_symbols"] != manifest["current_position_symbols"]
    assert manifest["filtered_symbols"] == []
    assert manifest["filter_reason"] is None


@pytest.mark.contract
def test_default_tech_core_loader_uses_operation_universe_not_legacy_instruments(monkeypatch, tmp_path):
    fixture = _write_tech_loader_fixture(tmp_path)
    _patch_runtime_config(monkeypatch, fixture["config_dir"])
    output_dir = tmp_path / "out"

    result = main_module.run_pipeline(
        watchlist_path=fixture["watchlist_path"],
        stale_rules_path=fixture["stale_rules_path"],
        mock_prices_path=fixture["mock_prices_path"],
        manual_prices_path=fixture["manual_prices_path"],
        output_dir=output_dir,
        provider_mode="mock",
        profile="tech",
        strict=True,
    )
    manifest = json.loads((output_dir / "layer_manifest.json").read_text(encoding="utf-8"))
    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")

    assert result.exit_code == 0
    assert result.runtime["universe_name"] == "tech_core"
    assert manifest["configured_symbol_count"] == 25
    assert manifest["loaded_symbol_count"] == 25
    assert manifest["configured_symbols"] == fixture["operation_symbols"]
    assert manifest["loaded_symbols"] == fixture["operation_symbols"]
    assert manifest["current_position_symbols"] == fixture["current_position_symbols"]
    assert manifest["operation_validator_symbols"] == fixture["operation_validator_symbols"]
    assert manifest["strict_required_symbols"] == fixture["strict_required_symbols"]
    assert manifest["filtered_symbols"] == []
    assert list(df["symbol"]) == fixture["operation_symbols"]
    validator_rows = df[df["symbol"].isin(fixture["operation_validator_symbols"])]
    assert set(validator_rows["required_for_operation"].astype(bool)) == {False}
    assert set(validator_rows["usable_for_operation"].astype(bool)) == {False}
    assert len(fixture["operation_candidate_symbols"]) == 19
    assert len(fixture["watchlist_symbols"]) == 28
    assert len(fixture["scan_symbols"]) == 41


@pytest.mark.contract
def test_current_tech_layer_manifest_counts():
    for layer_name in ["tech_core", "tech_operation_candidates", "tech_watchlist", "tech_scan_ai"]:
        assert load_target_layer_manifest(layer_name, [])["configured_symbol_count"] == _configured_count(layer_name)


@pytest.mark.contract
def test_current_energy_layer_manifest_counts():
    expected = {
        "energy_core": 4,
        "energy_operation_candidates": 8,
        "energy_watchlist": 24,
        "energy_scan": 41,
    }

    for layer_name, count in expected.items():
        manifest = load_target_layer_manifest(layer_name, [])
        assert manifest["account"] == "energy"
        assert manifest["configured_symbol_count"] == count
        assert manifest["root_mirror_match"] is True
        assert manifest["account_bootstrapped"] is True


@pytest.mark.contract
def test_config_check_root_mirror_and_registry(tmp_path):
    result = run_config_check(tmp_path)

    assert (tmp_path / "tech_layer_config_check.md").exists()
    assert (tmp_path / "tech_layer_config_check.json").exists()
    assert result["universes"]["tech_core"]["configured_symbol_count"] == _configured_count("tech_core")
    assert result["universes"]["tech_operation_candidates"]["root_mirror_matches"] is True
    assert result["universes"]["tech_watchlist"]["root_mirror_matches"] is True
    assert result["universes"]["tech_scan_ai"]["root_mirror_matches"] is True
    assert result["missing_registry_symbols"] == []


@pytest.mark.contract
def test_run_pipeline_writes_layer_manifest_and_reports(tmp_path):
    output_dir = tmp_path / "operation_candidates"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", quote_purpose="reference", universe="tech_operation_candidates")

    manifest = json.loads((output_dir / "layer_manifest.json").read_text(encoding="utf-8"))
    assert manifest["configured_symbol_count"] == _configured_count("tech_operation_candidates")
    assert manifest["loaded_symbol_count"] == _configured_count("tech_operation_candidates")
    assert manifest["config_mismatch"] is False
    assert "Config Source / Layer Manifest" in (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    assert "Config Source / Layer Manifest" in (output_dir / "debug_bundle.md").read_text(encoding="utf-8")
    assert "Config Source / Layer Manifest" in (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")
    assert "Config Source / Layer Manifest" in (output_dir / "runtime_diagnostics.md").read_text(encoding="utf-8")


@pytest.mark.contract
def test_energy_pipeline_writes_layer_manifest_and_reports(tmp_path):
    output_dir = tmp_path / "energy_scan"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="energy", quote_purpose="reference", universe="energy_scan")

    manifest = json.loads((output_dir / "layer_manifest.json").read_text(encoding="utf-8"))
    assert manifest["account"] == "energy"
    assert manifest["configured_symbol_count"] == 41
    assert manifest["loaded_symbol_count"] == 41
    assert manifest["config_mismatch"] is False
    assert manifest["root_mirror_match"] is True
    assert "Config Source / Layer Manifest" in (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")


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

    assert "check_account_layer_config.ps1" in script
    assert "-Account tech" in script


@pytest.mark.script
def test_pipeline_summary_declares_layer_config_summary():
    script = Path("scripts/run_tech_research_pipeline.ps1").read_text(encoding="utf-8")

    assert "## Layer Config Summary" in script
    assert "pipeline_layer_manifest.json" in script
    assert "CONFIG_MISMATCH: true" in script


def _write_tech_loader_fixture(tmp_path: Path) -> dict[str, object]:
    config_dir = tmp_path / "config"
    universes_dir = config_dir / "universes"
    universes_dir.mkdir(parents=True)
    operation_symbols = [f"000{i:03d}.SZ" for i in range(1, 26)]
    current_position_symbols = operation_symbols[:20]
    operation_validator_symbols = operation_symbols[20:]
    strict_required_symbols = operation_symbols[:7]
    operation_candidate_symbols = operation_symbols[:19]
    watchlist_symbols = operation_symbols + [f"001{i:03d}.SZ" for i in range(1, 4)]
    scan_symbols = watchlist_symbols + [f"002{i:03d}.SZ" for i in range(1, 14)]

    _write_universe(universes_dir / "tech_core.yaml", "tech_core", "core_holdings", "operation", operation_symbols)
    _write_universe(
        universes_dir / "tech_operation_candidates.yaml",
        "tech_operation_candidates",
        "operation_candidate",
        "reference",
        operation_candidate_symbols,
    )
    _write_universe(universes_dir / "tech_watchlist.yaml", "tech_watchlist", "candidate_watchlist", "reference", watchlist_symbols)
    _write_universe(universes_dir / "tech_scan_ai.yaml", "tech_scan_ai", "scan_universe", "reference", scan_symbols)

    _write_yaml(
        config_dir / "watchlist.yaml",
        {
            "projects": {
                "tech": {
                    "display_name": "tech",
                    "allow_full_detail": True,
                    "instruments": [
                        {
                            "symbol": symbol,
                            "name": symbol,
                            "market": "CN",
                            "provider": "mock",
                            "required_for_operation": symbol in strict_required_symbols,
                        }
                        for symbol in current_position_symbols
                    ],
                    "layer_universes": {
                        "operation": operation_symbols,
                        "operation_candidate": operation_candidate_symbols,
                        "watchlist": watchlist_symbols,
                        "scan": scan_symbols,
                    },
                }
            }
        },
    )
    _write_registry(config_dir / "symbol_registry.yaml", scan_symbols, strict_required_symbols, operation_validator_symbols)
    _write_yaml(config_dir / "stale_rules.yaml", {"default": {"max_age_seconds_open": 900, "max_age_seconds_closed": 900}, "markets": {}})
    _write_yaml(config_dir / "manual_prices.yaml", {"manual_prices": []})
    _write_mock_prices(config_dir / "mock_prices.yaml", operation_symbols)

    return {
        "config_dir": config_dir,
        "watchlist_path": config_dir / "watchlist.yaml",
        "stale_rules_path": config_dir / "stale_rules.yaml",
        "mock_prices_path": config_dir / "mock_prices.yaml",
        "manual_prices_path": config_dir / "manual_prices.yaml",
        "operation_symbols": operation_symbols,
        "current_position_symbols": current_position_symbols,
        "operation_validator_symbols": operation_validator_symbols,
        "strict_required_symbols": strict_required_symbols,
        "operation_candidate_symbols": operation_candidate_symbols,
        "watchlist_symbols": watchlist_symbols,
        "scan_symbols": scan_symbols,
    }


def _patch_runtime_config(monkeypatch: pytest.MonkeyPatch, config_dir: Path) -> None:
    monkeypatch.setattr(main_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(main_module, "UNIVERSES_DIR", config_dir / "universes")
    monkeypatch.setattr(main_module, "SYMBOL_REGISTRY_PATH", config_dir / "symbol_registry.yaml")
    monkeypatch.setattr(config_observability, "PROJECT_ROOT", config_dir.parent)
    monkeypatch.setattr(config_observability, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_observability, "UNIVERSES_DIR", config_dir / "universes")
    monkeypatch.setattr(config_observability, "WATCHLIST_PATH", config_dir / "watchlist.yaml")
    monkeypatch.setattr(config_observability, "REGISTRY_PATH", config_dir / "symbol_registry.yaml")


def _write_universe(path: Path, name: str, universe_type: str, quote_purpose: str, symbols: list[str]) -> None:
    _write_yaml(
        path,
        {
            "name": name,
            "profile": "tech",
            "universe_type": universe_type,
            "quote_purpose": quote_purpose,
            "symbols": symbols,
        },
    )


def _write_registry(path: Path, symbols: list[str], strict_required_symbols: list[str], validator_symbols: list[str]) -> None:
    registry = {}
    for symbol in symbols:
        registry[symbol] = {
            "symbol": symbol,
            "name": symbol,
            "market": "SZ",
            "asset_type": "ETF",
            "project_scope": "tech",
            "role": "operation_validator_etf" if symbol in validator_symbols else "core_holding_etf",
            "universe_tags": ["tech", "operation"],
            "required_for_operation": symbol in strict_required_symbols,
            "default_quote_purpose": "operation",
            "provider_preference": {"operation": ["mock"], "reference": ["mock"], "reconcile": ["mock"]},
            "report_group": "fixture",
            "enabled": True,
            "usable_for_operation": symbol not in validator_symbols,
            "affect_core_strict": symbol not in validator_symbols,
        }
    _write_yaml(path, registry)


def _write_mock_prices(path: Path, symbols: list[str]) -> None:
    quote_time = datetime.now(timezone.utc).isoformat()
    _write_yaml(
        path,
        {
            "prices": [
                {
                    "symbol": symbol,
                    "price": round(1.0 + index / 1000, 4),
                    "currency": "CNY",
                    "source": "mock",
                    "quote_time": quote_time,
                    "fetch_time": quote_time,
                    "market_status": "closed",
                }
                for index, symbol in enumerate(symbols)
            ]
        },
    )


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
