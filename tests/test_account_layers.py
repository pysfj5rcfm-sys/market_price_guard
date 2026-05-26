from __future__ import annotations

import shutil
from argparse import Namespace
from pathlib import Path

import yaml

from market_price_guard.account_config import account_layer_paths, normalize_layer
from market_price_guard.config_observability import run_config_check
from market_price_guard.manage_account_layers import AccountLayerManager, main as account_main


def _copy_project_config(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(Path("config"), root / "config")
    return root


def test_account_architecture_doc_exists():
    text = Path("docs/ACCOUNT_ARCHITECTURE.md").read_text(encoding="utf-8")

    assert "market_price_guard is not tech-only" in text
    assert "- tech" in text
    assert "- energy" in text
    assert "scope classification" in text.lower()


def test_account_path_resolver_returns_tech_paths():
    paths = account_layer_paths("tech")

    assert paths.layer_files["operation"] == "config/universes/tech_core.yaml"
    assert paths.layer_files["operation_candidate"] == "config/universes/tech_operation_candidates.yaml"
    assert paths.layer_files["watchlist"] == "config/universes/tech_watchlist.yaml"
    assert paths.layer_files["scan"] == "config/universes/tech_scan_ai.yaml"
    assert paths.project_path == "projects.tech"


def test_account_path_resolver_returns_future_energy_paths():
    paths = account_layer_paths("energy")

    assert paths.layer_files["operation"] == "config/universes/energy_core.yaml"
    assert paths.layer_files["operation_candidate"] == "config/universes/energy_operation_candidates.yaml"
    assert paths.layer_files["watchlist"] == "config/universes/energy_watchlist.yaml"
    assert paths.layer_files["scan"] == "config/universes/energy_scan.yaml"
    assert paths.project_path == "projects.energy"


def test_account_generic_layer_aliases():
    assert normalize_layer("tech_core", account="tech") == "operation"
    assert normalize_layer("tech_scan_ai", account="tech") == "scan"
    assert normalize_layer("energy_core", account="energy") == "operation"
    assert normalize_layer("energy_operation_candidates", account="energy") == "operation_candidate"
    assert normalize_layer("energy_watchlist", account="energy") == "watchlist"
    assert normalize_layer("energy_scan", account="energy") == "scan"


def test_account_config_check_tech_counts(tmp_path):
    result = run_config_check(tmp_path, account="tech")

    assert result["account"] == "tech"
    assert result["account_bootstrapped"] is True
    assert result["universes"]["tech_core"]["configured_symbol_count"] == 7
    assert result["universes"]["tech_operation_candidates"]["configured_symbol_count"] == 11
    assert result["universes"]["tech_watchlist"]["configured_symbol_count"] == 16
    assert result["universes"]["tech_scan_ai"]["configured_symbol_count"] == 30
    assert (tmp_path / "tech_layer_config_check.md").exists()


def test_account_config_check_energy_not_bootstrapped(tmp_path):
    result = run_config_check(tmp_path, account="energy")

    assert result["account"] == "energy"
    assert result["account_bootstrapped"] is False
    assert "config/universes/energy_operation_candidates.yaml" in result["missing_account_config_files"]
    assert "config/universes/energy_watchlist.yaml" in result["missing_account_config_files"]
    assert "config/universes/energy_scan.yaml" in result["missing_account_config_files"]
    assert "tech_core" not in result["universes"]


def test_manage_account_layers_tech_show_validate_export(tmp_path):
    root = _copy_project_config(tmp_path)
    manager = AccountLayerManager("tech", root)

    show = manager.run(Namespace(account="tech", command="show"))
    validate = manager.run(Namespace(account="tech", command="validate"))
    export = manager.run(Namespace(account="tech", command="export"))

    assert show["account"] == "tech"
    assert show["after_counts"] == {"operation": 7, "operation_candidate": 11, "watchlist": 16, "scan": 30}
    assert validate["validation_status"] == "ok"
    assert export["after_counts"]["scan"] == 30


def test_manage_account_layers_energy_does_not_fallback_to_tech(tmp_path):
    root = _copy_project_config(tmp_path)
    manager = AccountLayerManager("energy", root)

    report = manager.run(Namespace(account="energy", command="show"))

    assert report["account"] == "energy"
    assert report["account_bootstrapped"] is False
    assert report["symbols"] == {}
    assert "config/universes/energy_operation_candidates.yaml" in report["missing_account_config_files"]


def test_manage_account_layers_energy_validate_reports_missing_files(tmp_path):
    root = _copy_project_config(tmp_path)

    exit_code = account_main(["--project-root", str(root), "-Account", "energy", "validate"])

    report_text = (root / "outputs_config_manager_latest/config_manager_report.md").read_text(encoding="utf-8")
    assert exit_code == 1
    assert "account: energy" in report_text
    assert "account_bootstrapped: false" in report_text
    assert "config/universes/energy_scan.yaml" in report_text


def test_manage_account_layers_dry_run_makes_no_config_changes(tmp_path):
    root = _copy_project_config(tmp_path)
    before = (root / "config/watchlist.yaml").read_bytes()

    exit_code = account_main(["--project-root", str(root), "-Account", "tech", "add", "513180.SH", "-Layer", "watchlist", "-DryRun"])

    assert exit_code == 0
    assert (root / "config/watchlist.yaml").read_bytes() == before
    data = yaml.safe_load((root / "config/universes/tech_watchlist.yaml").read_text(encoding="utf-8"))
    assert "513180.SH" not in data["symbols"]


def test_account_scripts_declared():
    check_script = Path("scripts/check_account_layer_config.ps1").read_text(encoding="utf-8")
    manage_script = Path("scripts/manage_account_layers.ps1").read_text(encoding="utf-8")
    tech_check_wrapper = Path("scripts/check_tech_layer_config.ps1").read_text(encoding="utf-8")

    assert "market_price_guard.check_account_layer_config" in check_script
    assert "market_price_guard.manage_account_layers" in manage_script
    assert "check_account_layer_config.ps1" in tech_check_wrapper
