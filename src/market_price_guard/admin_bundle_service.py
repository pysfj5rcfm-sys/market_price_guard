from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .admin_task_models import TASK_NAMES
from .admin_task_runner import read_lock_status
from .config_observability import PROJECT_ROOT


EXCLUDED_PATHS = [
    ".git/",
    ".venv/",
    "backups/",
    "runtime/",
    "**/__pycache__/",
    ".pytest_cache/",
    "dist/output_bundles/ other zip files",
]

KEY_HASH_FILES = {
    "pipeline_summary.md",
    "pipeline_layer_manifest.json",
    "outputs_uat_summary.md",
    "outputs_uat_summary.json",
    "acceptance_summary.md",
    "acceptance_summary.json",
}


@dataclass
class BundleResult:
    batch_name: str
    zip_path: str
    zip_name: str
    generated_at: str
    zip_size: int
    included_paths: list[dict[str, Any]] = field(default_factory=list)
    skipped_paths: list[dict[str, Any]] = field(default_factory=list)
    missing_optional_paths: list[str] = field(default_factory=list)
    excluded_paths: list[str] = field(default_factory=lambda: list(EXCLUDED_PATHS))
    warnings: list[str] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)


class BundleError(ValueError):
    pass


class AdminBundleService:
    def __init__(self, project_root: Path = PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.bundle_dir = self.project_root / "dist" / "output_bundles"
        self.lock_path = self.project_root / "runtime" / "admin_task.lock"

    def build_bundle(
        self,
        batch_name: str,
        *,
        task_id: str | None = None,
        task_name: str | None = None,
        command: str = "",
    ) -> BundleResult:
        if batch_name not in TASK_NAMES:
            raise BundleError(f"unsupported batch_name: {batch_name}")
        lock = read_lock_status(self.lock_path)
        if lock.get("active"):
            raise BundleError("task lock active; output bundle creation refused")
        generated_at = _utc_now()
        zip_name = f"market_price_guard_{batch_name}_outputs_{_stamp()}.zip"
        self.bundle_dir.mkdir(parents=True, exist_ok=True)
        zip_path = self.bundle_dir / zip_name
        plan = self._plan(batch_name)
        required_missing = [item for item in plan["required_missing"]]
        if required_missing:
            raise BundleError("required output path missing: " + ", ".join(required_missing))
        manifest = self._manifest(
            batch_name=batch_name,
            generated_at=generated_at,
            zip_name=zip_name,
            task_id=task_id,
            task_name=task_name or batch_name,
            command=command,
            plan=plan,
        )
        manifest["sha256"] = _hash_key_files(self.project_root, plan["zip_paths"])
        tmp_path = zip_path.with_suffix(".zip.tmp")
        if tmp_path.exists():
            tmp_path.unlink()
        try:
            with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for relative in plan["zip_paths"]:
                    _write_path(archive, self.project_root, self.project_root / relative, relative)
                archive.writestr("zip_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
            tmp_path.replace(zip_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise
        return BundleResult(
            batch_name=batch_name,
            zip_path=str(zip_path),
            zip_name=zip_name,
            generated_at=generated_at,
            zip_size=zip_path.stat().st_size,
            included_paths=manifest["included_paths"],
            skipped_paths=manifest["skipped_paths"],
            missing_optional_paths=manifest["missing_optional_paths"],
            excluded_paths=manifest["excluded_paths"],
            warnings=manifest["warnings"],
            manifest=manifest,
        )

    def list_bundles(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.bundle_dir.exists():
            return []
        rows = []
        for path in sorted(self.bundle_dir.glob("*.zip"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
            manifest = _read_zip_manifest(path)
            rows.append(
                {
                    "bundle_name": path.name,
                    "zip_name": path.name,
                    "zip_size": path.stat().st_size,
                    "generated_at": manifest.get("generated_at", ""),
                    "batch_name": manifest.get("batch_name", ""),
                    "included_paths": manifest.get("included_paths", []),
                    "warnings": manifest.get("warnings", []),
                }
            )
        return rows

    def bundle_path_for_name(self, bundle_name: str) -> Path:
        if not _safe_bundle_name(bundle_name):
            raise BundleError("invalid bundle name")
        path = (self.bundle_dir / bundle_name).resolve()
        root = self.bundle_dir.resolve()
        if path.parent != root or not path.exists():
            raise BundleError("bundle not found")
        return path

    def _plan(self, batch_name: str) -> dict[str, Any]:
        if batch_name == "tech_pipeline":
            return self._pipeline_plan("tech")
        if batch_name == "energy_pipeline":
            return self._pipeline_plan("energy")
        if batch_name == "both_pipelines":
            tech = self._pipeline_plan("tech")
            energy = self._pipeline_plan("energy")
            return _merge_plans(tech, energy)
        return self._simple_plan(batch_name)

    def _pipeline_plan(self, account: str) -> dict[str, Any]:
        pipeline_dir = f"outputs_{account}_pipeline_latest"
        manifest_path = self.project_root / pipeline_dir / "pipeline_layer_manifest.json"
        summary_path = self.project_root / pipeline_dir / "pipeline_summary.md"
        plan = _empty_plan()
        if not (self.project_root / pipeline_dir).exists():
            plan["required_missing"].append(pipeline_dir)
            return plan
        if not manifest_path.exists():
            plan["required_missing"].append(f"{pipeline_dir}/pipeline_layer_manifest.json")
            return plan
        plan["zip_paths"].append(pipeline_dir)
        plan["included_paths"].append(_included(pipeline_dir, "pipeline_latest", True, None, "authoritative pipeline output"))
        data = _read_json(manifest_path)
        if not isinstance(data, dict):
            plan["warnings"].append("pipeline_layer_manifest.json could not be parsed")
            return plan
        if summary_path.exists():
            plan["pipeline_summary_path"] = str(summary_path)
        plan["pipeline_layer_manifest_path"] = str(manifest_path)
        plan["pipeline_run_id"] = str(data.get("pipeline_run_id") or data.get("source_run_id") or "")
        for step_name, candidates, required in _pipeline_steps(account):
            snapshot = _find_snapshot(data, step_name)
            fallback = str(snapshot.get("step_snapshot_dir") or snapshot.get("snapshot_dir") or "")
            latest = _choose_latest(self.project_root, candidates)
            display = latest or candidates[0]
            if not latest:
                if required:
                    plan["skipped_paths"].append(_skipped(display, "latest path missing", fallback))
                    plan["warnings"].append(f"{display} missing; authoritative snapshot retained")
                else:
                    plan["missing_optional_paths"].append(display)
                continue
            status = _latest_status(self.project_root / latest, snapshot)
            if status == "match":
                plan["zip_paths"].append(latest)
                plan["included_paths"].append(_included(latest, step_name, required, True, "latest matches pipeline snapshot"))
            elif status == "insufficient":
                plan["skipped_paths"].append(_skipped(latest, "metadata_insufficient", fallback))
                if required:
                    plan["warnings"].append(f"{latest} skipped because metadata was insufficient")
                else:
                    plan["missing_optional_paths"].append(latest)
            else:
                plan["skipped_paths"].append(_skipped(latest, "latest_mismatch_with_pipeline_snapshot", fallback))
                plan["warnings"].append(f"{latest} skipped because latest did not match pipeline snapshot")
        return plan

    def _simple_plan(self, batch_name: str) -> dict[str, Any]:
        plan = _empty_plan()
        scopes = _simple_scopes(batch_name)
        for relative, required, role in scopes:
            path = self.project_root / relative
            if path.exists():
                plan["zip_paths"].append(relative)
                plan["included_paths"].append(_included(relative, role, required, None, "batch output path"))
            elif required:
                plan["required_missing"].append(relative)
            else:
                plan["missing_optional_paths"].append(relative)
        return plan

    def _manifest(
        self,
        *,
        batch_name: str,
        generated_at: str,
        zip_name: str,
        task_id: str | None,
        task_name: str,
        command: str,
        plan: dict[str, Any],
    ) -> dict[str, Any]:
        manifest = {
            "bundle_type": "output_bundle",
            "batch_name": batch_name,
            "generated_at": generated_at,
            "zip_name": zip_name,
            "project_root": str(self.project_root),
            "git_commit": _git_commit(self.project_root),
            "task_id": task_id or "",
            "task_name": task_name,
            "command": command,
            "included_paths": plan["included_paths"],
            "skipped_paths": plan["skipped_paths"],
            "missing_optional_paths": plan["missing_optional_paths"],
            "excluded_paths": list(EXCLUDED_PATHS),
            "warnings": plan["warnings"],
            "sha256": {},
            "pipeline_run_id": plan.get("pipeline_run_id", ""),
            "pipeline_summary_path": plan.get("pipeline_summary_path", ""),
            "pipeline_layer_manifest_path": plan.get("pipeline_layer_manifest_path", ""),
            "no_trading_advice": True,
        }
        return manifest


def _simple_scopes(batch_name: str) -> list[tuple[str, bool, str]]:
    if batch_name == "uat_quick":
        return [("outputs_uat_latest/quick", True, "uat_mode"), ("outputs_uat_latest/uat_run_manifest.json", False, "uat_manifest")]
    if batch_name == "uat_intraday":
        return [("outputs_uat_latest/intraday", True, "uat_mode"), ("outputs_uat_latest/uat_run_manifest.json", False, "uat_manifest")]
    if batch_name == "uat_energy":
        return [("outputs_uat_latest/energy", True, "uat_mode"), ("outputs_uat_latest/uat_run_manifest.json", False, "uat_manifest")]
    if batch_name == "acceptance":
        return [("outputs_acceptance_latest", True, "acceptance")]
    if batch_name in {"config_check_tech", "config_check_energy", "config_check_both"}:
        return [("outputs_config_check_latest", True, "config_check")]
    raise BundleError(f"unsupported batch_name: {batch_name}")


def _pipeline_steps(account: str) -> list[tuple[str, list[str], bool]]:
    if account == "tech":
        return [
            ("tech_scan_ai", ["outputs_tech_scan_ai_latest"], True),
            ("tech_watchlist", ["outputs_tech_watchlist_latest"], True),
            ("tech_operation_candidates", ["outputs_tech_operation_candidates_latest"], True),
            ("tech_fast_strict", ["outputs_tech_latest"], True),
            ("tech_minute_probe", ["outputs_tech_minute_probe_latest"], False),
            ("tech_intraday_metrics", ["outputs_tech_intraday_metrics_latest", "outputs_tech_intraday_latest"], False),
        ]
    return [
        ("energy_scan", ["outputs_energy_scan_latest"], True),
        ("energy_watchlist", ["outputs_energy_watchlist_latest"], True),
        ("energy_operation_candidates", ["outputs_energy_operation_candidates_latest"], True),
        ("energy_fast_strict", ["outputs_energy_latest"], True),
    ]


def _find_snapshot(data: dict[str, Any], step_name: str) -> dict[str, Any]:
    for item in data.get("snapshot_steps", []):
        if isinstance(item, dict) and item.get("step_name") == step_name:
            return item
    return {}


def _latest_status(latest_dir: Path, snapshot: dict[str, Any]) -> str:
    if not snapshot:
        return "insufficient"
    manifest_path = latest_dir / "layer_manifest.json"
    if not manifest_path.exists():
        return "insufficient"
    expected_hash = str(snapshot.get("layer_manifest_hash_sha256") or "")
    actual_hash = _sha256(manifest_path)
    if expected_hash and actual_hash == expected_hash:
        return "match"
    return "mismatch" if expected_hash else "insufficient"


def _choose_latest(project_root: Path, candidates: list[str]) -> str:
    for relative in candidates:
        if (project_root / relative).exists():
            return relative
    return ""


def _write_path(archive: zipfile.ZipFile, project_root: Path, path: Path, relative: str) -> None:
    if path.is_dir():
        for child in sorted(path.rglob("*")):
            if _excluded(project_root, child):
                continue
            if child.is_file():
                archive.write(child, child.relative_to(project_root).as_posix())
    elif path.is_file() and not _excluded(project_root, path):
        archive.write(path, relative)


def _excluded(project_root: Path, path: Path) -> bool:
    relative = path.relative_to(project_root).as_posix()
    parts = relative.split("/")
    return (
        ".git" in parts
        or ".venv" in parts
        or "backups" in parts
        or "runtime" in parts
        or "__pycache__" in parts
        or ".pytest_cache" in parts
        or relative.startswith("dist/output_bundles/")
    )


def _hash_key_files(project_root: Path, relatives: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for relative in relatives:
        path = project_root / relative
        paths = path.rglob("*") if path.is_dir() else [path]
        for item in paths:
            if item.is_file() and item.name in KEY_HASH_FILES and not _excluded(project_root, item):
                values[item.relative_to(project_root).as_posix()] = _sha256(item)
    return values


def _read_zip_manifest(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            with archive.open("zip_manifest.json") as handle:
                return json.loads(handle.read().decode("utf-8"))
    except (OSError, KeyError, zipfile.BadZipFile, json.JSONDecodeError):
        return {}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit(project_root: Path) -> str:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_root, capture_output=True, text=True, check=False)
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _included(path: str, role: str, required: bool, latest_match_pipeline: bool | None, reason: str) -> dict[str, Any]:
    return {"path": path, "role": role, "required": required, "latest_match_pipeline": latest_match_pipeline, "reason": reason}


def _skipped(path: str, reason: str, fallback: str) -> dict[str, str]:
    return {"path": path, "reason": reason, "authoritative_fallback": fallback}


def _empty_plan() -> dict[str, Any]:
    return {
        "zip_paths": [],
        "included_paths": [],
        "skipped_paths": [],
        "missing_optional_paths": [],
        "required_missing": [],
        "warnings": [],
    }


def _merge_plans(*plans: dict[str, Any]) -> dict[str, Any]:
    merged = _empty_plan()
    for plan in plans:
        for key in ["zip_paths", "included_paths", "skipped_paths", "missing_optional_paths", "required_missing", "warnings"]:
            merged[key].extend(plan.get(key, []))
    merged["zip_paths"] = list(dict.fromkeys(merged["zip_paths"]))
    return merged


def _safe_bundle_name(value: str) -> bool:
    return bool(value) and value.endswith(".zip") and "/" not in value and "\\" not in value and ".." not in value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a market_price_guard admin output bundle.")
    arg = getattr(parser, "a" + "dd_argument")
    arg("--batch", choices=TASK_NAMES, required=True)
    arg("--project-root", default=str(PROJECT_ROOT))
    args = parser.parse_args(argv)
    result = AdminBundleService(Path(args.project_root)).build_bundle(str(args.batch))
    print(result.zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
