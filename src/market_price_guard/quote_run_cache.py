from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from .models import RawPrice


ENV_USE_QUOTE_CACHE = "MARKET_GUARD_USE_QUOTE_RUN_CACHE"
ENV_QUOTE_CACHE_DIR = "MARKET_GUARD_QUOTE_RUN_CACHE_DIR"


def is_enabled() -> bool:
    return os.environ.get(ENV_USE_QUOTE_CACHE) == "1" and bool(os.environ.get(ENV_QUOTE_CACHE_DIR))


def cache_dir() -> Path:
    configured = os.environ.get(ENV_QUOTE_CACHE_DIR)
    return Path(configured) if configured else Path("outputs_quote_run_cache_latest")


def read_quote(key: dict[str, str]) -> tuple[RawPrice | None, dict[str, object]]:
    if not is_enabled():
        return None, _event("disabled", key, "quote_run_cache_disabled")
    directory = cache_dir()
    path = _quote_path(directory, key)
    if not path.exists():
        _update_manifest(directory, quote_cache_miss_count=1)
        insufficient = _find_profile_insufficient(directory, key)
        if insufficient:
            _update_manifest(directory, quote_cache_profile_insufficient_count=1)
            return None, _event("profile_insufficient", key, "cache_hit_but_profile_insufficient", cache_file=insufficient)
        return None, _event("miss", key, "quote_cache_miss", cache_file=path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw = RawPrice.model_validate(payload["raw"])
    except Exception as exc:
        _update_manifest(directory, quote_cache_miss_count=1, cache_error_count=1)
        return None, _event("error", key, "quote_cache_read_error", cache_file=path, exception=exc)
    _update_manifest(
        directory,
        quote_cache_hit_count=1,
        quote_cache_success_hit_count=1 if raw.price is not None else 0,
        quote_cache_failure_hit_count=1 if raw.price is None else 0,
        repeated_provider_call_prevented_count=1,
    )
    return _as_cache_hit(raw, payload, key, path), _event("hit", key, "quote_cache_hit", cache_file=path)


def write_quote(key: dict[str, str], raw: RawPrice) -> None:
    if not is_enabled():
        return
    directory = cache_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = _quote_path(directory, key)
    payload = {
        "cache_key": _key_string(key),
        "written_at_utc": _now_iso(),
        "key": key,
        "raw": raw.model_dump(mode="json"),
        "cacheable": True,
        "cache_source": {
            "selected_provider": raw.provider_diagnostics.get("selected_provider", raw.source),
            "source_provider": raw.source,
            "source_layer": key.get("layer", ""),
            "source_quote_purpose": key.get("quote_purpose", ""),
            "source_runtime_profile": key.get("runtime_profile", ""),
        },
    }
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        _update_manifest(directory, cache_error_count=1)


def load_manifest(directory: Path | None = None) -> dict[str, Any]:
    path = (directory or cache_dir()) / "quote_cache_manifest.json"
    if not path.exists():
        return _default_manifest()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _default_manifest()
    manifest = _default_manifest()
    manifest.update(data)
    return manifest


def initialize(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "quotes").mkdir(parents=True, exist_ok=True)
    _write_manifest(directory, _default_manifest())


def quote_key(
    *,
    account: str,
    symbol: str,
    normalized_symbol: str,
    quote_purpose: str,
    provider_profile: str,
    runtime_profile: str,
    market: str,
    asset_type: str,
    layer: str,
) -> dict[str, str]:
    return {
        "account": account,
        "symbol": symbol,
        "normalized_symbol": normalized_symbol,
        "quote_purpose": quote_purpose,
        "provider_profile": provider_profile,
        "runtime_profile": runtime_profile,
        "market": market,
        "asset_type": asset_type,
        "layer": layer,
    }


def _as_cache_hit(raw: RawPrice, payload: dict[str, Any], key: dict[str, str], path: Path) -> RawPrice:
    cached = raw.model_copy(deep=True)
    diagnostics = deepcopy(cached.provider_diagnostics)
    source = payload.get("cache_source", {}) if isinstance(payload.get("cache_source"), dict) else {}
    diagnostics.update(
        {
            "cache_hit": True,
            "cache_miss": False,
            "cache_source": source,
            "cache_file": str(path),
            "cache_key": _key_string(key),
            "cacheable": True,
            "repeated_call_prevented": True,
            "repeated_provider_call_prevented": True,
            "provider_planned_chain": diagnostics.get("provider_planned_chain", []),
            "actual_provider_attempted": [],
            "provider_skip_reasons": diagnostics.get("provider_skip_reasons", {}),
            "provider_attempts": [],
            "source_provider_attempts": diagnostics.get("provider_attempts", []),
            "source_actual_provider_attempted": diagnostics.get("actual_provider_attempted", []),
        }
    )
    cached.provider_diagnostics = diagnostics
    return cached


def _find_profile_insufficient(directory: Path, key: dict[str, str]) -> Path | None:
    quote_dir = directory / "quotes"
    if not quote_dir.exists():
        return None
    target_account = key.get("account", "")
    target_symbol = key.get("normalized_symbol", key.get("symbol", ""))
    target_purpose = key.get("quote_purpose", "")
    if target_purpose != "operation":
        return None
    for path in quote_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        stored_key = payload.get("key", {})
        if (
            isinstance(stored_key, dict)
            and stored_key.get("account") == target_account
            and stored_key.get("normalized_symbol") == target_symbol
            and stored_key.get("quote_purpose") == "reference"
        ):
            return path
    return None


def _quote_path(directory: Path, key: dict[str, str]) -> Path:
    return directory / "quotes" / (_safe_filename(_key_string(key)) + ".json")


def _key_string(key: dict[str, str]) -> str:
    parts = [
        key.get("account", ""),
        key.get("normalized_symbol", key.get("symbol", "")),
        key.get("quote_purpose", ""),
        key.get("provider_profile", ""),
        key.get("runtime_profile", ""),
        key.get("market", ""),
        key.get("asset_type", ""),
    ]
    return "|".join(str(part) for part in parts)


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in value)


def _default_manifest() -> dict[str, Any]:
    return {
        "generated_at": _now_iso(),
        "quote_cache_hit_count": 0,
        "quote_cache_miss_count": 0,
        "quote_cache_success_hit_count": 0,
        "quote_cache_failure_hit_count": 0,
        "quote_cache_profile_insufficient_count": 0,
        "repeated_provider_call_prevented_count": 0,
        "cache_error_count": 0,
    }


def _update_manifest(directory: Path, **deltas: int) -> None:
    manifest = load_manifest(directory)
    for key, delta in deltas.items():
        manifest[key] = int(manifest.get(key, 0)) + int(delta)
    _write_manifest(directory, manifest)


def _write_manifest(directory: Path, manifest: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "quotes").mkdir(parents=True, exist_ok=True)
    (directory / "quote_cache_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _event(status: str, key: dict[str, str], reason: str, *, cache_file: Path | None = None, exception: Exception | None = None) -> dict[str, object]:
    return {
        "cache_scope": "quote_run",
        "cache_status": status,
        "cache_key": _key_string(key),
        "cache_file": str(cache_file or ""),
        "cache_reason": reason,
        "exception_type": type(exception).__name__ if exception else "",
        "exception_message": str(exception) if exception else "",
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
