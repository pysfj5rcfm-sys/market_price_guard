from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from market_price_guard.manage_tech_layers import TechLayerManager, main, normalize_layer, policy_warnings_for_symbol


def _copy_project_config(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(Path("config"), root / "config")
    return root


def _read_symbols(root: Path, relative: str) -> list[str]:
    data = yaml.safe_load((root / relative).read_text(encoding="utf-8"))
    return [str(symbol) for symbol in data["symbols"]]


def _read_root_layer(root: Path, layer: str) -> list[str]:
    data = yaml.safe_load((root / "config/watchlist.yaml").read_text(encoding="utf-8"))
    return [str(symbol) for symbol in data["projects"]["tech"]["layer_universes"][layer]]


def _tech_counts(root: Path) -> dict[str, int]:
    return {
        "operation": len(_read_symbols(root, "config/universes/tech_core.yaml")),
        "operation_candidate": len(_read_symbols(root, "config/universes/tech_operation_candidates.yaml")),
        "watchlist": len(_read_symbols(root, "config/universes/tech_watchlist.yaml")),
        "scan": len(_read_symbols(root, "config/universes/tech_scan_ai.yaml")),
    }


def test_layer_aliases():
    assert normalize_layer("core") == "operation"
    assert normalize_layer("candidate") == "operation_candidate"
    assert normalize_layer("tech_scan_ai") == "scan"


def test_show_does_not_modify_files(tmp_path):
    root = _copy_project_config(tmp_path)
    before = (root / "config/watchlist.yaml").read_bytes()

    report = TechLayerManager(root).show()

    assert report["before_counts"] == _tech_counts(root)
    assert report["root_mirror_mismatch"] is False
    assert (root / "config/watchlist.yaml").read_bytes() == before


def test_validate_runs_config_check(tmp_path):
    root = _copy_project_config(tmp_path)

    report = TechLayerManager(root).validate()

    assert report["validation_status"] == "ok"
    assert (root / "outputs_config_check_latest/tech_layer_config_check.md").exists()


def test_add_symbol_to_watchlist_updates_universe_and_root(tmp_path):
    root = _copy_project_config(tmp_path)
    manager = TechLayerManager(root)

    report = manager.add("513310.SH", "watchlist", dry_run=False, backup=False, confirm_policy_override=True, allow_operation_layer=False)

    assert report["errors"] == []
    assert "513310.SH" in _read_symbols(root, "config/universes/tech_watchlist.yaml")
    assert "513310.SH" in _read_root_layer(root, "watchlist")


def test_add_duplicate_symbol_is_noop(tmp_path):
    root = _copy_project_config(tmp_path)

    report = TechLayerManager(root).add("512480.SH", "watchlist", dry_run=False, backup=False, confirm_policy_override=False, allow_operation_layer=False)

    assert report["errors"] == []
    assert any("already in watchlist" in item for item in report["structural_warnings"])
    assert _read_symbols(root, "config/universes/tech_watchlist.yaml").count("512480.SH") == 1


def test_remove_symbol_from_watchlist_updates_both_files(tmp_path):
    root = _copy_project_config(tmp_path)

    report = TechLayerManager(root).remove("512480.SH", "watchlist", dry_run=False, backup=False, allow_operation_layer=False)

    assert report["errors"] == []
    assert "512480.SH" not in _read_symbols(root, "config/universes/tech_watchlist.yaml")
    assert "512480.SH" not in _read_root_layer(root, "watchlist")


def test_move_candidate_to_watchlist_updates_both_files(tmp_path):
    root = _copy_project_config(tmp_path)

    report = TechLayerManager(root).move(
        "588890.SH",
        "operation_candidate",
        "watchlist",
        dry_run=False,
        backup=False,
        confirm_policy_override=False,
        allow_operation_layer=False,
    )

    assert report["errors"] == []
    assert "588890.SH" not in _read_symbols(root, "config/universes/tech_operation_candidates.yaml")
    assert "588890.SH" in _read_symbols(root, "config/universes/tech_watchlist.yaml")
    assert "588890.SH" not in _read_root_layer(root, "operation_candidate")
    assert "588890.SH" in _read_root_layer(root, "watchlist")


def test_sync_root_rebuilds_root_from_universes(tmp_path):
    root = _copy_project_config(tmp_path)
    watchlist_path = root / "config/watchlist.yaml"
    data = yaml.safe_load(watchlist_path.read_text(encoding="utf-8"))
    data["projects"]["tech"]["layer_universes"]["watchlist"] = ["BROKEN.SZ"]
    watchlist_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    report = TechLayerManager(root).sync_root(dry_run=False, backup=False)

    assert report["errors"] == []
    assert _read_root_layer(root, "watchlist") == _read_symbols(root, "config/universes/tech_watchlist.yaml")


def test_operation_add_requires_allow_operation_layer(tmp_path):
    root = _copy_project_config(tmp_path)

    blocked = TechLayerManager(root).add("512480.SH", "operation", dry_run=True, backup=False, confirm_policy_override=False, allow_operation_layer=False)
    allowed = TechLayerManager(root).add("512480.SH", "operation", dry_run=True, backup=False, confirm_policy_override=False, allow_operation_layer=True)

    assert blocked["errors"]
    assert "operation layer modification requires -AllowOperationLayer" in blocked["errors"]
    assert "operation layer modification requires -AllowOperationLayer" not in allowed["errors"]


def test_policy_warning_symbol_requires_override_for_actual_candidate_change(tmp_path):
    root = _copy_project_config(tmp_path)

    TechLayerManager(root).remove("002463.SZ", "operation_candidate", dry_run=False, backup=False, allow_operation_layer=False)
    blocked = TechLayerManager(root).add("002463.SZ", "operation_candidate", dry_run=False, backup=False, confirm_policy_override=False, allow_operation_layer=False)
    allowed = TechLayerManager(root).add("002463.SZ", "operation_candidate", dry_run=False, backup=False, confirm_policy_override=True, allow_operation_layer=False)

    assert "policy warning requires -ConfirmPolicyOverride" in blocked["errors"]
    assert allowed["errors"] == []
    assert allowed["policy_override_used"] is True
    assert "002463.SZ" in _read_symbols(root, "config/universes/tech_operation_candidates.yaml")


def test_special_symbols_are_policy_warnings_not_hard_blocks():
    registry = yaml.safe_load(Path("config/symbol_registry.yaml").read_text(encoding="utf-8"))

    assert any("event_stock_candidate_warning" in item for item in policy_warnings_for_symbol("002463.SZ", "operation_candidate", registry["002463.SZ"]))
    assert any("failed_trial_observation_only" in item for item in policy_warnings_for_symbol("159516.SZ", "operation_candidate", registry["159516.SZ"]))
    assert any("manual_price_only_candidate_warning" in item for item in policy_warnings_for_symbol("GOLD_CNY", "operation_candidate", registry["GOLD_CNY"]))
    assert any("non_tech_candidate_warning" in item for item in policy_warnings_for_symbol("510300.SH", "operation_candidate", registry["510300.SH"]))


def test_missing_registry_symbol_is_rejected_by_default(tmp_path):
    root = _copy_project_config(tmp_path)

    report = TechLayerManager(root).add("999999.SZ", "scan", dry_run=False, backup=False, confirm_policy_override=False, allow_operation_layer=False)

    assert "symbol not found in config/symbol_registry.yaml" in report["errors"]
    assert "999999.SZ" not in _read_symbols(root, "config/universes/tech_scan_ai.yaml")


def test_dry_run_makes_no_file_changes(tmp_path):
    root = _copy_project_config(tmp_path)
    before = (root / "config/universes/tech_watchlist.yaml").read_bytes()

    report = TechLayerManager(root).add("513180.SH", "watchlist", dry_run=True, backup=False, confirm_policy_override=True, allow_operation_layer=False)

    assert report["dry_run"] is True
    assert (root / "config/universes/tech_watchlist.yaml").read_bytes() == before


def test_backup_creates_backup_directory(tmp_path):
    root = _copy_project_config(tmp_path)

    report = TechLayerManager(root).backup_command()

    backup_path = Path(report["backup_path"])
    assert backup_path.exists()
    assert (backup_path / "config/watchlist.yaml").exists()
    assert (backup_path / "config/symbol_registry.yaml").exists()


def test_show_and_export_report_counts(tmp_path):
    root = _copy_project_config(tmp_path)
    manager = TechLayerManager(root)

    show = manager.show()
    export = manager.export()

    assert show["after_counts"]["scan"] == _tech_counts(root)["scan"]
    assert export["after_counts"]["watchlist"] == _tech_counts(root)["watchlist"]
    data = json.loads((root / "outputs_config_manager_latest/tech_layer_config_export.json").read_text(encoding="utf-8"))
    assert len(data["layers"]["operation"]) == _tech_counts(root)["operation"]


def test_manage_script_declared():
    script = Path("scripts/manage_tech_layers.ps1").read_text(encoding="utf-8")

    assert "market_price_guard.manage_tech_layers" in script
    assert "ValueFromRemainingArguments" in script


def test_main_accepts_powershell_style_options(tmp_path):
    root = _copy_project_config(tmp_path)

    exit_code = main(["--project-root", str(root), "add", "513310.SH", "-Layer", "watchlist", "-DryRun"])

    assert exit_code == 0
    assert "513310.SH" not in _read_symbols(root, "config/universes/tech_watchlist.yaml")
