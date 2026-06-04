from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .admin_task_models import TASK_NAMES
from .config_observability import PROJECT_ROOT


SUMMARY_PATHS: dict[str, list[str]] = {
    "tech_pipeline": [
        "outputs_tech_pipeline_latest/pipeline_summary.md",
        "outputs_tech_pipeline_latest/pipeline_manifest.json",
        "outputs_tech_pipeline_latest/pipeline_layer_manifest.json",
    ],
    "energy_pipeline": [
        "outputs_energy_pipeline_latest/pipeline_summary.md",
        "outputs_energy_pipeline_latest/pipeline_manifest.json",
        "outputs_energy_pipeline_latest/pipeline_layer_manifest.json",
    ],
    "both_pipelines": [
        "outputs_tech_pipeline_latest/pipeline_summary.md",
        "outputs_energy_pipeline_latest/pipeline_summary.md",
        "outputs_tech_pipeline_latest/pipeline_manifest.json",
        "outputs_energy_pipeline_latest/pipeline_manifest.json",
    ],
    "uat_quick": [
        "outputs_uat_latest/quick/outputs_uat_summary.md",
        "outputs_uat_latest/quick/outputs_uat_summary.json",
        "outputs_uat_latest/uat_run_manifest.json",
    ],
    "uat_intraday": [
        "outputs_uat_latest/intraday/outputs_uat_summary.md",
        "outputs_uat_latest/intraday/outputs_uat_summary.json",
        "outputs_uat_latest/uat_run_manifest.json",
    ],
    "uat_energy": [
        "outputs_uat_latest/energy/outputs_uat_summary.md",
        "outputs_uat_latest/energy/outputs_uat_summary.json",
        "outputs_uat_latest/uat_run_manifest.json",
    ],
    "acceptance": [
        "outputs_acceptance_latest/acceptance_summary.md",
        "outputs_acceptance_latest/acceptance_summary.json",
    ],
    "config_check_tech": [
        "outputs_config_check_latest/tech_layer_config_check.md",
        "outputs_config_check_latest/tech_layer_config_check.json",
    ],
    "config_check_energy": [
        "outputs_config_check_latest/energy_layer_config_check.md",
        "outputs_config_check_latest/energy_layer_config_check.json",
    ],
    "config_check_both": [
        "outputs_config_check_latest/tech_layer_config_check.md",
        "outputs_config_check_latest/energy_layer_config_check.md",
        "outputs_config_check_latest/tech_layer_config_check.json",
        "outputs_config_check_latest/energy_layer_config_check.json",
    ],
}

OUTPUT_PATHS: dict[str, list[str]] = {
    "tech_pipeline": [
        "outputs_tech_pipeline_latest",
        "outputs_tech_scan_ai_latest",
        "outputs_tech_watchlist_latest",
        "outputs_tech_operation_candidates_latest",
        "outputs_tech_latest",
        "outputs_tech_minute_probe_latest",
        "outputs_tech_intraday_metrics_latest",
        "outputs_tech_intraday_latest",
    ],
    "energy_pipeline": [
        "outputs_energy_pipeline_latest",
        "outputs_energy_scan_latest",
        "outputs_energy_watchlist_latest",
        "outputs_energy_operation_candidates_latest",
        "outputs_energy_latest",
    ],
    "both_pipelines": [
        "outputs_tech_pipeline_latest",
        "outputs_tech_scan_ai_latest",
        "outputs_tech_watchlist_latest",
        "outputs_tech_operation_candidates_latest",
        "outputs_tech_latest",
        "outputs_tech_minute_probe_latest",
        "outputs_tech_intraday_metrics_latest",
        "outputs_tech_intraday_latest",
        "outputs_energy_pipeline_latest",
        "outputs_energy_scan_latest",
        "outputs_energy_watchlist_latest",
        "outputs_energy_operation_candidates_latest",
        "outputs_energy_latest",
    ],
    "uat_quick": ["outputs_uat_latest/quick", "outputs_uat_latest/uat_run_manifest.json"],
    "uat_intraday": ["outputs_uat_latest/intraday", "outputs_uat_latest/uat_run_manifest.json"],
    "uat_energy": ["outputs_uat_latest/energy", "outputs_uat_latest/uat_run_manifest.json"],
    "acceptance": ["outputs_acceptance_latest"],
    "config_check_tech": ["outputs_config_check_latest"],
    "config_check_energy": ["outputs_config_check_latest"],
    "config_check_both": ["outputs_config_check_latest"],
}


def summary_paths_for(task_name: str, project_root: Path = PROJECT_ROOT) -> list[str]:
    if task_name not in TASK_NAMES:
        return []
    return [str(project_root / item) for item in SUMMARY_PATHS.get(task_name, []) if (project_root / item).exists()]


def output_paths_for(task_name: str, project_root: Path = PROJECT_ROOT) -> list[str]:
    if task_name not in TASK_NAMES:
        return []
    return [str(project_root / item) for item in OUTPUT_PATHS.get(task_name, []) if (project_root / item).exists()]


def read_summary_preview(task_name: str, project_root: Path = PROJECT_ROOT, *, max_lines: int = 24) -> dict[str, Any]:
    paths = SUMMARY_PATHS.get(task_name, [])
    previews = []
    metrics: dict[str, Any] = {}
    for item in paths:
        path = project_root / item
        if not path.exists():
            continue
        if path.suffix.lower() == ".json":
            data = _read_json(path)
            if isinstance(data, dict):
                metrics.update(_metrics_from_json(data))
        if path.suffix.lower() in {".md", ".txt"}:
            previews.append({"path": str(path), "text": _head(path, max_lines=max_lines)})
    snapshot_paths = _snapshot_presence(task_name, project_root)
    return {
        "summary_paths": [str(project_root / item) for item in paths if (project_root / item).exists()],
        "metrics": metrics,
        "previews": previews,
        "snapshot_paths": snapshot_paths,
    }


def has_runtime_warning(task_name: str, project_root: Path = PROJECT_ROOT) -> bool:
    preview = read_summary_preview(task_name, project_root)
    metrics = preview.get("metrics", {})
    try:
        return int(metrics.get("runtime_warnings", 0)) > 0
    except (TypeError, ValueError):
        return False


def reported_status_from_summary(task_name: str, project_root: Path = PROJECT_ROOT) -> str:
    preview = read_summary_preview(task_name, project_root)
    metrics = preview.get("metrics", {})
    if _int_metric(metrics, "failed") > 0 or _int_metric(metrics, "failed_count") > 0:
        return "failed"
    if _int_metric(metrics, "strict_blocked_but_reported") > 0:
        return "strict_blocked_but_reported"
    if _int_metric(metrics, "runtime_warnings") > 0:
        return "runtime_warning"
    return "passed"


def _metrics_from_json(data: dict[str, Any]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    summary = data.get("summary")
    if isinstance(summary, dict):
        for key in ["passed", "failed", "strict_blocked_but_reported", "runtime_warnings", "total_elapsed_seconds"]:
            if key in summary:
                metrics[key] = summary[key]
    for key in [
        "passed",
        "failed",
        "strict_blocked_but_reported",
        "runtime_warnings",
        "total_elapsed_seconds",
        "status",
        "failed_count",
    ]:
        if key in data:
            metrics[key] = data[key]
    if "layer_mismatch_count" in data:
        metrics["layer_mismatch_count"] = data["layer_mismatch_count"]
    return metrics


def _snapshot_presence(task_name: str, project_root: Path) -> list[dict[str, Any]]:
    result = []
    for item in ["outputs_tech_pipeline_latest/snapshots", "outputs_energy_pipeline_latest/snapshots"]:
        if task_name in {"tech_pipeline", "both_pipelines"} and "tech" not in item:
            continue
        if task_name in {"energy_pipeline", "both_pipelines"} and "energy" not in item:
            continue
        if task_name not in {"tech_pipeline", "energy_pipeline", "both_pipelines"}:
            continue
        path = project_root / item
        result.append({"path": str(path), "exists": path.exists()})
    return result


def _head(path: Path, *, max_lines: int) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:max_lines])
    except OSError as exc:
        return f"Could not read preview: {exc}"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _int_metric(metrics: dict[str, Any], key: str) -> int:
    try:
        return int(metrics.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0
