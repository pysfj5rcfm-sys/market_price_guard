from __future__ import annotations

import shutil
from argparse import Namespace
from pathlib import Path

import yaml

from market_price_guard.account_config import account_layer_paths, normalize_layer
from market_price_guard.config_observability import run_config_check
from market_price_guard.manage_account_layers import AccountLayerManager, main as account_main

ENERGY_OPERATION = ["00883.HK", "601899.SH", "601985.SH", "003816.SZ"]
ENERGY_OPERATION_CANDIDATES = [
    "600938.SH",
    "600900.SH",
    "601088.SH",
    "600489.SH",
    "600547.SH",
    "603993.SH",
    "600188.SH",
    "600795.SH",
]
ENERGY_WATCHLIST = [
    *ENERGY_OPERATION,
    *ENERGY_OPERATION_CANDIDATES,
    "600028.SH",
    "601857.SH",
    "601225.SH",
    "600011.SH",
    "600027.SH",
    "600905.SH",
    "600886.SH",
    "000975.SZ",
    "000630.SZ",
    "000878.SZ",
    "600362.SH",
    "601600.SH",
]
ENERGY_SCAN = [
    *ENERGY_WATCHLIST,
    "601808.SH",
    "600583.SH",
    "600256.SH",
    "002128.SZ",
    "000983.SZ",
    "600348.SH",
    "601001.SH",
    "600985.SH",
    "000933.SZ",
    "600988.SH",
    "603979.SH",
    "600497.SH",
    "000807.SZ",
    "002155.SZ",
    "600021.SH",
    "600642.SH",
    "000027.SZ",
]


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


def test_account_config_check_energy_bootstrapped(tmp_path):
    result = run_config_check(tmp_path, account="energy")

    assert result["account"] == "energy"
    assert result["scope_classification"] == "energy-only layer pool expansion"
    assert result["account_bootstrapped"] is True
    assert result["missing_account_config_files"] == []
    assert result["root_mirror_match"] is True
    assert result["universes"]["energy_core"]["configured_symbol_count"] == 4
    assert result["universes"]["energy_operation_candidates"]["configured_symbol_count"] == 8
    assert result["universes"]["energy_watchlist"]["configured_symbol_count"] == 24
    assert result["universes"]["energy_scan"]["configured_symbol_count"] == 41
    assert result["missing_registry_symbols"] == []
    assert "tech_core" not in result["universes"]
    assert (tmp_path / "energy_layer_config_check.md").exists()


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
    assert report["account_bootstrapped"] is True
    assert report["after_counts"] == {"operation": 4, "operation_candidate": 8, "watchlist": 24, "scan": 41}
    assert report["symbols"]["operation"] == ENERGY_OPERATION
    assert "159632.SZ" not in report["symbols"]["operation"]
    assert report["missing_account_config_files"] == []


def test_manage_account_layers_energy_validate_export_and_sync_root(tmp_path):
    root = _copy_project_config(tmp_path)

    exit_code = account_main(["--project-root", str(root), "-Account", "energy", "validate"])
    export_code = account_main(["--project-root", str(root), "-Account", "energy", "export"])
    sync_code = account_main(["--project-root", str(root), "-Account", "energy", "sync-root", "-DryRun"])

    report_text = (root / "outputs_config_manager_latest/config_manager_report.md").read_text(encoding="utf-8")
    export_json = root / "outputs_config_manager_latest/energy_layer_config_export.json"
    export_md = root / "outputs_config_manager_latest/energy_layer_config_export.md"
    export_csv = root / "outputs_config_manager_latest/energy_layer_config_export.csv"
    assert exit_code == 0
    assert export_code == 0
    assert sync_code == 0
    assert "account: energy" in report_text
    assert "account_bootstrapped: true" in report_text
    assert "root_mirror_match: true" in report_text
    assert export_json.exists()
    assert export_md.exists()
    assert export_csv.exists()


def test_energy_bootstrap_config_files_and_registry_are_present():
    energy_files = [
        "config/universes/energy_core.yaml",
        "config/universes/energy_operation_candidates.yaml",
        "config/universes/energy_watchlist.yaml",
        "config/universes/energy_scan.yaml",
    ]
    for relative in energy_files:
        assert Path(relative).exists()

    core = yaml.safe_load(Path("config/universes/energy_core.yaml").read_text(encoding="utf-8"))
    candidates = yaml.safe_load(Path("config/universes/energy_operation_candidates.yaml").read_text(encoding="utf-8"))
    watchlist = yaml.safe_load(Path("config/universes/energy_watchlist.yaml").read_text(encoding="utf-8"))
    scan = yaml.safe_load(Path("config/universes/energy_scan.yaml").read_text(encoding="utf-8"))
    root = yaml.safe_load(Path("config/watchlist.yaml").read_text(encoding="utf-8"))
    registry = yaml.safe_load(Path("config/symbol_registry.yaml").read_text(encoding="utf-8"))

    assert core["symbols"] == ENERGY_OPERATION
    assert candidates["symbols"] == ENERGY_OPERATION_CANDIDATES
    assert watchlist["symbols"] == ENERGY_WATCHLIST
    assert scan["symbols"] == ENERGY_SCAN
    assert root["projects"]["energy"]["layer_universes"]["operation"] == core["symbols"]
    assert root["projects"]["energy"]["layer_universes"]["operation_candidate"] == candidates["symbols"]
    assert root["projects"]["energy"]["layer_universes"]["watchlist"] == watchlist["symbols"]
    assert root["projects"]["energy"]["layer_universes"]["scan"] == scan["symbols"]
    for symbol in ENERGY_SCAN:
        assert symbol in registry
        assert registry[symbol]["project_scope"] == "energy"
        assert "tech-only" not in str(registry[symbol]).lower()
        assert "energy" in registry[symbol].get("universe_tags", [])


def test_account_manager_root_mirror_match_semantics_are_consistent(tmp_path):
    root = _copy_project_config(tmp_path)

    exit_code = account_main(["--project-root", str(root), "-Account", "energy", "show"])

    report_text = (root / "outputs_config_manager_latest/config_manager_report.md").read_text(encoding="utf-8")
    report_json = yaml.safe_load((root / "outputs_config_manager_latest/config_manager_report.json").read_text(encoding="utf-8"))
    assert exit_code == 0
    assert report_json["root_mirror_mismatch"] is False
    assert report_json["root_mirror_match"] is True
    assert "ROOT_MIRROR_MISMATCH: false" in report_text
    assert "root_mirror_match: true" in report_text


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
