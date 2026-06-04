from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from market_price_guard.admin_bundle_service import AdminBundleService


TECH_STEPS = [
    ("tech_scan_ai", "outputs_tech_scan_ai_latest", True),
    ("tech_watchlist", "outputs_tech_watchlist_latest", True),
    ("tech_operation_candidates", "outputs_tech_operation_candidates_latest", True),
    ("tech_fast_strict", "outputs_tech_latest", True),
    ("tech_minute_probe", "outputs_tech_minute_probe_latest", False),
    ("tech_intraday_metrics", "outputs_tech_intraday_latest", False),
]

ENERGY_STEPS = [
    ("energy_scan", "outputs_energy_scan_latest", True),
    ("energy_watchlist", "outputs_energy_watchlist_latest", True),
    ("energy_operation_candidates", "outputs_energy_operation_candidates_latest", True),
    ("energy_fast_strict", "outputs_energy_latest", True),
]


def test_tech_pipeline_bundle_includes_matching_latest_paths(tmp_path):
    _fake_pipeline(tmp_path, "tech", TECH_STEPS)

    result = AdminBundleService(tmp_path).build_bundle("tech_pipeline")

    manifest = _manifest(Path(result.zip_path))
    names = _names(Path(result.zip_path))
    included = {item["path"]: item for item in manifest["included_paths"]}
    assert "outputs_tech_pipeline_latest/pipeline_summary.md" in names
    for _, relative, _ in TECH_STEPS:
        assert f"{relative}/layer_manifest.json" in names
        assert included[relative]["latest_match_pipeline"] is True
    assert manifest["pipeline_run_id"] == "tech-run-1"
    assert "outputs_tech_pipeline_latest/pipeline_summary.md" in manifest["sha256"]
    assert "outputs_tech_pipeline_latest/pipeline_layer_manifest.json" in manifest["sha256"]


def test_energy_pipeline_bundle_includes_four_layers_and_no_intraday_paths(tmp_path):
    _fake_pipeline(tmp_path, "energy", ENERGY_STEPS)
    (tmp_path / "outputs_tech_minute_probe_latest").mkdir()
    (tmp_path / "outputs_tech_intraday_latest").mkdir()

    result = AdminBundleService(tmp_path).build_bundle("energy_pipeline")

    names = _names(Path(result.zip_path))
    for _, relative, _ in ENERGY_STEPS:
        assert f"{relative}/layer_manifest.json" in names
    assert not any("minute_probe" in item for item in names)
    assert not any("intraday" in item for item in names)


def test_latest_mismatch_is_skipped_with_snapshot_fallback(tmp_path):
    _fake_pipeline(tmp_path, "tech", TECH_STEPS[:4])
    (tmp_path / "outputs_tech_watchlist_latest/layer_manifest.json").write_text('{"changed": true}\n', encoding="utf-8")

    result = AdminBundleService(tmp_path).build_bundle("tech_pipeline")

    manifest = _manifest(Path(result.zip_path))
    names = _names(Path(result.zip_path))
    skipped = {item["path"]: item for item in manifest["skipped_paths"]}
    assert "outputs_tech_watchlist_latest/layer_manifest.json" not in names
    assert skipped["outputs_tech_watchlist_latest"]["reason"] == "latest_mismatch_with_pipeline_snapshot"
    assert "outputs_tech_pipeline_latest/snapshots/tech_watchlist" in skipped["outputs_tech_watchlist_latest"]["authoritative_fallback"]
    assert manifest["warnings"]


def test_zip_manifest_exists_and_records_included_skipped_missing_excluded_sha(tmp_path):
    _fake_pipeline(tmp_path, "tech", TECH_STEPS[:4])

    result = AdminBundleService(tmp_path).build_bundle("tech_pipeline")

    with zipfile.ZipFile(result.zip_path) as archive:
        assert "zip_manifest.json" in archive.namelist()
    manifest = _manifest(Path(result.zip_path))
    assert manifest["included_paths"]
    assert isinstance(manifest["skipped_paths"], list)
    assert manifest["missing_optional_paths"]
    assert "runtime/" in manifest["excluded_paths"]
    assert manifest["sha256"]


def _fake_pipeline(tmp_path: Path, account: str, steps: list[tuple[str, str, bool]]) -> None:
    pipeline_dir = tmp_path / f"outputs_{account}_pipeline_latest"
    snapshot_root = pipeline_dir / "snapshots"
    snapshot_root.mkdir(parents=True)
    (pipeline_dir / "pipeline_summary.md").write_text(
        f"# {account} pipeline\n- passed: 4\n- failed: 0\n- runtime_warnings: 0\n",
        encoding="utf-8",
    )
    snapshots = []
    for step_name, relative, _ in steps:
        latest_dir = tmp_path / relative
        latest_dir.mkdir(parents=True)
        content = json.dumps({"step": step_name, "account": account}, sort_keys=True) + "\n"
        (latest_dir / "layer_manifest.json").write_text(content, encoding="utf-8")
        (latest_dir / "0_upload_bundle.md").write_text("data/report generation only\n", encoding="utf-8")
        snapshot_dir = snapshot_root / step_name
        snapshot_dir.mkdir(parents=True)
        (snapshot_dir / "layer_manifest.json").write_text(content, encoding="utf-8")
        snapshots.append(
            {
                "step_name": step_name,
                "step_output_dir": relative,
                "step_snapshot_dir": str(snapshot_dir),
                "source_run_id": f"{account}-run-1",
                "generated_at": "2026-06-04T00:00:00Z",
                "layer_manifest_hash_sha256": _sha(snapshot_dir / "layer_manifest.json"),
            }
        )
    data = {
        "pipeline_name": f"{account}_research_pipeline",
        "pipeline_run_id": f"{account}-run-1",
        "source_run_id": f"{account}-run-1",
        "snapshot_steps": snapshots,
    }
    (pipeline_dir / "pipeline_layer_manifest.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _manifest(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as archive:
        return json.loads(archive.read("zip_manifest.json").decode("utf-8"))


def _names(zip_path: Path) -> set[str]:
    with zipfile.ZipFile(zip_path) as archive:
        return set(archive.namelist())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
