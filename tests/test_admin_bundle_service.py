from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from market_price_guard.admin_bundle_service import AdminBundleService, BundleError


def test_bundle_service_creates_zip_name_with_batch(tmp_path):
    (tmp_path / "outputs_acceptance_latest").mkdir()
    (tmp_path / "outputs_acceptance_latest/acceptance_summary.md").write_text("summary\n", encoding="utf-8")

    result = AdminBundleService(tmp_path).build_bundle("acceptance")

    assert result.zip_name.startswith("market_price_guard_acceptance_outputs_")
    assert result.zip_name.endswith(".zip")
    assert Path(result.zip_path).exists()


def test_simple_bundle_manifest_contains_required_sections(tmp_path):
    (tmp_path / "outputs_uat_latest/quick").mkdir(parents=True)
    (tmp_path / "outputs_uat_latest/quick/outputs_uat_summary.md").write_text("uat\n", encoding="utf-8")
    (tmp_path / "outputs_uat_latest/quick/outputs_uat_summary.json").write_text('{"failed": 0}\n', encoding="utf-8")
    (tmp_path / "outputs_uat_latest/uat_run_manifest.json").write_text('{"latest_mode": "quick"}\n', encoding="utf-8")

    result = AdminBundleService(tmp_path).build_bundle("uat_quick")

    manifest = _manifest(Path(result.zip_path))
    assert manifest["batch_name"] == "uat_quick"
    assert manifest["included_paths"]
    assert manifest["skipped_paths"] == []
    assert ".git/" in manifest["excluded_paths"]
    assert ".venv/" in manifest["excluded_paths"]
    assert "backups/" in manifest["excluded_paths"]
    assert "runtime/" in manifest["excluded_paths"]
    assert "outputs_uat_latest/quick/outputs_uat_summary.md" in manifest["sha256"]
    assert manifest["no_trading_advice"] is True


def test_required_simple_output_missing_fails_gracefully(tmp_path):
    with pytest.raises(BundleError, match="required output path missing"):
        AdminBundleService(tmp_path).build_bundle("uat_quick")


def test_bundle_download_path_guard_blocks_traversal(tmp_path):
    service = AdminBundleService(tmp_path)

    with pytest.raises(BundleError):
        service.bundle_path_for_name("../outside.zip")


def _manifest(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as archive:
        return json.loads(archive.read("zip_manifest.json").decode("utf-8"))


def _names(zip_path: Path) -> set[str]:
    with zipfile.ZipFile(zip_path) as archive:
        return set(archive.namelist())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
