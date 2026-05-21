from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd


ENV_USE_CACHE = "MARKET_GUARD_USE_UAT_RUN_CACHE"
ENV_CACHE_DIR = "MARKET_GUARD_UAT_RUN_CACHE_DIR"

ENABLED_PROVIDER = "akshare"
ENABLED_FUNCTION = "fund_etf_spot_em"
ENABLED_CACHE_KEY = f"{ENABLED_PROVIDER}.{ENABLED_FUNCTION}"
DEFAULT_TTL_SECONDS = 0


def is_uat_run_cache_enabled(function_name: str) -> bool:
    return (
        os.environ.get(ENV_USE_CACHE) == "1"
        and bool(os.environ.get(ENV_CACHE_DIR))
        and function_name == ENABLED_FUNCTION
    )


def cache_file_path(cache_dir: Path | None = None) -> Path:
    return _cache_dir(cache_dir) / "akshare_fund_etf_spot_em.csv"


def manifest_path(cache_dir: Path | None = None) -> Path:
    return _cache_dir(cache_dir) / "cache_manifest.json"


def read_cached_dataframe(function_name: str) -> tuple[pd.DataFrame | None, dict[str, object]]:
    now = _now_iso()
    if not is_uat_run_cache_enabled(function_name):
        return None, _attempt("bypass", now, "uat_run_cache_not_enabled")

    directory = _cache_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = cache_file_path(directory)
    if not path.exists():
        _update_manifest(directory, miss_delta=1, notes="cache file missing; live fetch required")
        return None, _attempt("miss", now, "cache_file_missing", cache_file=path)

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        _update_manifest(directory, bypass_delta=1, error_delta=1, notes=f"cache read failed: {type(exc).__name__}")
        return None, _attempt(
            "bypass",
            now,
            "cache_read_error",
            cache_file=path,
            exception_type=type(exc).__name__,
            exception_message=str(exc),
        )

    _update_manifest(directory, hit_delta=1, row_count=len(df), notes="cache hit")
    return df, _attempt("hit", now, "cache_hit", cache_file=path, row_count=len(df))


def write_cached_dataframe(function_name: str, df: pd.DataFrame | None) -> dict[str, object]:
    now = _now_iso()
    if not is_uat_run_cache_enabled(function_name):
        return _attempt("not_applicable", now, "uat_run_cache_not_enabled")
    if df is None:
        return _attempt("bypass", now, "no_dataframe_to_cache")

    directory = _cache_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = cache_file_path(directory)
    try:
        df.to_csv(path, index=False, encoding="utf-8")
    except Exception as exc:
        _update_manifest(directory, bypass_delta=1, error_delta=1, notes=f"cache write failed: {type(exc).__name__}")
        return _attempt(
            "bypass",
            now,
            "cache_write_error",
            cache_file=path,
            exception_type=type(exc).__name__,
            exception_message=str(exc),
        )

    _update_manifest(directory, row_count=len(df), notes="cache written")
    return _attempt("write", now, "cache_written", cache_file=path, row_count=len(df))


def load_manifest(cache_dir: Path | None = None) -> dict[str, Any]:
    path = manifest_path(cache_dir)
    if not path.exists():
        return _default_manifest()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _default_manifest()
    base = _default_manifest()
    base.update(data)
    return base


def initialize_cache_dir(cache_dir: Path) -> dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest = _default_manifest()
    manifest["generated_at"] = _now_iso()
    _write_manifest(cache_dir, manifest)
    return manifest


def _cache_dir(cache_dir: Path | None = None) -> Path:
    if cache_dir is not None:
        return cache_dir
    configured = os.environ.get(ENV_CACHE_DIR)
    if configured:
        return Path(configured)
    return Path("outputs_uat_run_cache_latest")


def _default_manifest() -> dict[str, Any]:
    return {
        "cache_run_id": str(uuid4()),
        "generated_at": _now_iso(),
        "provider": ENABLED_PROVIDER,
        "function_name": ENABLED_FUNCTION,
        "cache_key": ENABLED_CACHE_KEY,
        "ttl_seconds": DEFAULT_TTL_SECONDS,
        "row_count": 0,
        "source_mode": "uat_run_cache",
        "hit_count": 0,
        "miss_count": 0,
        "bypass_count": 0,
        "expired_count": 0,
        "cache_error_count": 0,
        "cache_file": str(cache_file_path(_cache_dir())),
        "notes": "",
    }


def _update_manifest(
    cache_dir: Path,
    *,
    hit_delta: int = 0,
    miss_delta: int = 0,
    bypass_delta: int = 0,
    error_delta: int = 0,
    row_count: int | None = None,
    notes: str = "",
) -> None:
    manifest = load_manifest(cache_dir)
    manifest["hit_count"] = int(manifest.get("hit_count", 0)) + hit_delta
    manifest["miss_count"] = int(manifest.get("miss_count", 0)) + miss_delta
    manifest["bypass_count"] = int(manifest.get("bypass_count", 0)) + bypass_delta
    manifest["cache_error_count"] = int(manifest.get("cache_error_count", 0)) + error_delta
    if row_count is not None:
        manifest["row_count"] = row_count
    manifest["cache_file"] = str(cache_file_path(cache_dir))
    if notes:
        manifest["notes"] = notes
    _write_manifest(cache_dir, manifest)


def _write_manifest(cache_dir: Path, manifest: dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path(cache_dir).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _attempt(
    cache_status: str,
    fetch_time_utc: str,
    reason: str,
    *,
    cache_file: Path | None = None,
    row_count: int | None = None,
    exception_type: str = "",
    exception_message: str = "",
) -> dict[str, object]:
    return {
        "cache_enabled": True,
        "cache_scope": "uat_run",
        "cache_status": cache_status,
        "cache_provider": ENABLED_PROVIDER,
        "cache_function": ENABLED_FUNCTION,
        "cache_key": ENABLED_CACHE_KEY,
        "cache_file": str(cache_file) if cache_file else str(cache_file_path()),
        "source_mode": "uat_run_cache",
        "reason": reason,
        "fetch_time_utc": fetch_time_utc,
        "returned_rows": "" if row_count is None else row_count,
        "exception_type": exception_type,
        "exception_message": exception_message,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
