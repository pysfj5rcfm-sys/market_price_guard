from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from market_price_guard.admin_layer_service import AdminLayerService


def _copy_project_config(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(Path("config"), root / "config")
    return root


def _config_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted((root / "config").rglob("*.yaml"))
    }


def _symbols(root: Path, relative: str) -> list[str]:
    data = yaml.safe_load((root / relative).read_text(encoding="utf-8"))
    return [str(item) for item in data["symbols"]]


def _root_layer(root: Path, account: str, layer: str) -> list[str]:
    data = yaml.safe_load((root / "config/watchlist.yaml").read_text(encoding="utf-8"))
    return [str(item) for item in data["projects"][account]["layer_universes"][layer]]


def test_admin_service_current_baselines_are_preserved():
    service = AdminLayerService(Path.cwd())

    tech = service.account_snapshot("tech")
    energy = service.account_snapshot("energy")

    assert tech["counts"] == {"operation": 7, "operation_candidate": 19, "watchlist": 28, "scan": 40}
    assert energy["counts"] == {"operation": 4, "operation_candidate": 8, "watchlist": 24, "scan": 41}


def test_admin_symbol_insert_dry_run_does_not_modify_config(tmp_path):
    root = _copy_project_config(tmp_path)
    before = _config_bytes(root)

    plan = AdminLayerService(root).plan_symbol_insert(
        account="tech",
        target_layer="scan",
        raw_symbol="601138.SH",
    )

    assert plan.operation_type == "add"
    assert plan.after_counts["scan"] == 41
    assert _config_bytes(root) == before


def test_admin_move_dry_run_does_not_modify_config(tmp_path):
    root = _copy_project_config(tmp_path)
    before = _config_bytes(root)

    plan = AdminLayerService(root).plan_move(
        account="tech",
        symbol="512480.SH",
        source_layer="scan",
        target_layer="watchlist",
    )

    assert plan.operation_type == "move"
    assert _config_bytes(root) == before


def test_admin_remove_dry_run_does_not_modify_config(tmp_path):
    root = _copy_project_config(tmp_path)
    before = _config_bytes(root)

    plan = AdminLayerService(root).plan_remove(
        account="tech",
        symbol="512480.SH",
        source_layer="watchlist",
    )

    assert plan.operation_type == "remove"
    assert plan.after_counts["watchlist"] == 27
    assert _config_bytes(root) == before


def test_admin_apply_requires_explicit_confirmation(tmp_path):
    root = _copy_project_config(tmp_path)
    service = AdminLayerService(root)

    plan = service.plan_symbol_insert(account="tech", target_layer="scan", raw_symbol="601138.SH")
    result = service.perform(plan)

    assert plan.apply_allowed is False
    assert result.success is False
    assert "apply confirmation required" in result.errors
    assert "601138.SH" not in _symbols(root, "config/universes/tech_scan_ai.yaml")


def test_admin_operation_layer_apply_requires_extra_confirmation(tmp_path):
    root = _copy_project_config(tmp_path)

    plan = AdminLayerService(root).plan_symbol_insert(
        account="tech",
        target_layer="operation",
        raw_symbol="601138.SH",
        confirm_apply=True,
    )

    assert plan.apply_allowed is False
    assert "operation layer confirmation required" in plan.blocking_reasons


def test_admin_apply_creates_backup_audit_validate_and_syncs_root(tmp_path):
    root = _copy_project_config(tmp_path)
    service = AdminLayerService(root)

    plan = service.plan_symbol_insert(
        account="tech",
        target_layer="scan",
        raw_symbol="601138.SH",
        confirm_apply=True,
    )
    result = service.perform(plan)

    assert result.success is True
    assert result.validation_status == "ok"
    backup_path = Path(result.backup_path)
    assert backup_path.exists()
    manifest = json.loads((backup_path / "backup_manifest.json").read_text(encoding="utf-8"))
    assert manifest["operation"] == "add"
    assert manifest["account"] == "tech"
    assert manifest["symbol"] == "601138.SH"
    assert manifest["user_action_source"] == "admin_ui"
    assert "601138.SH" in _symbols(root, "config/universes/tech_scan_ai.yaml")
    assert "601138.SH" in _root_layer(root, "tech", "scan")
    assert Path(result.audit_path).exists()
    audit_line = Path(result.audit_path).read_text(encoding="utf-8").strip().splitlines()[-1]
    assert json.loads(audit_line)["success"] is True


def test_admin_registry_missing_and_duplicate_warnings_visible(tmp_path):
    root = _copy_project_config(tmp_path)
    service = AdminLayerService(root)

    missing = service.plan_symbol_insert(account="tech", target_layer="scan", raw_symbol="000001.SZ", confirm_apply=True)
    duplicate = service.plan_symbol_insert(account="tech", target_layer="watchlist", raw_symbol="159632.SZ", confirm_apply=True)

    assert any("registry_missing" in item for item in missing.policy_warnings)
    assert any("already exists" in item for item in duplicate.structural_warnings + duplicate.policy_warnings)


def test_admin_registry_stub_can_keep_temp_validation_ok(tmp_path):
    root = _copy_project_config(tmp_path)
    service = AdminLayerService(root)

    plan = service.plan_symbol_insert(
        account="tech",
        target_layer="scan",
        raw_symbol="000001.SZ",
        display_name="Temp Symbol",
        instrument_type="A-share stock",
        create_registry_stub=True,
        confirm_apply=True,
    )
    result = service.perform(plan)

    assert result.success is True
    registry = yaml.safe_load((root / "config/symbol_registry.yaml").read_text(encoding="utf-8"))
    assert registry["000001.SZ"]["source"] == "admin_ui_stub"
    assert "000001.SZ" in _root_layer(root, "tech", "scan")
