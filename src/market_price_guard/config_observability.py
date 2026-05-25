from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
UNIVERSES_DIR = CONFIG_DIR / "universes"
WATCHLIST_PATH = CONFIG_DIR / "watchlist.yaml"
REGISTRY_PATH = CONFIG_DIR / "symbol_registry.yaml"

CONFIG_LOADER_NAME = "market_price_guard.config_observability"
CONFIG_LOADER_VERSION = "v0.7.3.2"

LAYER_TO_ROOT_MIRROR = {
    "tech_core": "operation",
    "tech_operation_candidates": "operation_candidate",
    "tech_watchlist": "watchlist",
    "tech_scan_ai": "scan",
}

TECH_LAYER_ORDER = [
    "tech_core",
    "tech_operation_candidates",
    "tech_watchlist",
    "tech_scan_ai",
]

FORBIDDEN_METADATA_KEYS = {
    "forbidden",
    "forbidden_symbols",
    "removed",
    "removed_symbols",
    "deleted",
    "deleted_symbols",
    "deleted_by_this_update",
    "audit",
    "notes",
    "examples",
    "restrictions",
    "changelog",
}


def extract_configured_symbols(data: Any, root_layer_name: str | None = None) -> list[str]:
    if not isinstance(data, dict):
        return []
    for key in ("symbols", "universe", "items", "instruments"):
        if key in data:
            return _symbols_from_value(data.get(key))
    if root_layer_name:
        layer_universes = (
            data.get("projects", {})
            .get("tech", {})
            .get("layer_universes", {})
        )
        if isinstance(layer_universes, dict):
            return _symbols_from_value(layer_universes.get(root_layer_name))
    return []


def build_layer_manifest(
    layer_name: str,
    universe_name: str,
    universe_type: str,
    config_source_path: Path | str,
    configured_symbols: list[str],
    loaded_symbols: list[str],
    *,
    root_watchlist_layer_name: str | None = None,
    legacy_fallback_used: bool = False,
    legacy_fallback_source_path: str | None = None,
    hardcoded_default_used: bool = False,
    hardcoded_default_reason: str = "",
    root_watchlist_layer_mirror_used: bool = False,
    config_load_status: str = "ok",
    config_load_warnings: list[str] | None = None,
    source_layer_manifest_path: str | None = None,
) -> dict[str, Any]:
    source = Path(config_source_path) if not isinstance(config_source_path, Path) else config_source_path
    display_source = _display_path(source)
    source_exists = source.exists() if not str(config_source_path).startswith("derived_from_") else False
    missing = [symbol for symbol in configured_symbols if symbol not in loaded_symbols]
    extra = [symbol for symbol in loaded_symbols if symbol not in configured_symbols]
    manifest = {
        "layer_name": layer_name,
        "universe_name": universe_name,
        "universe_type": universe_type,
        "config_source_path": display_source,
        "config_source_exists": source_exists,
        "config_source_hash_sha256": _sha256(source) if source_exists else "",
        "config_source_mtime": _mtime(source) if source_exists else "",
        "config_loader_name": CONFIG_LOADER_NAME,
        "config_loader_version": CONFIG_LOADER_VERSION,
        "configured_symbol_count": len(configured_symbols),
        "loaded_symbol_count": len(loaded_symbols),
        "configured_symbols": configured_symbols,
        "loaded_symbols": loaded_symbols,
        "missing_from_loaded": missing,
        "extra_loaded_symbols": extra,
        "duplicate_configured_symbols": _duplicates(configured_symbols),
        "duplicate_loaded_symbols": _duplicates(loaded_symbols),
        "legacy_fallback_used": legacy_fallback_used,
        "legacy_fallback_source_path": legacy_fallback_source_path,
        "hardcoded_default_used": hardcoded_default_used,
        "hardcoded_default_reason": hardcoded_default_reason,
        "root_watchlist_layer_mirror_used": root_watchlist_layer_mirror_used,
        "root_watchlist_layer_name": root_watchlist_layer_name,
        "config_mismatch": bool(missing or extra),
        "config_load_status": config_load_status,
        "config_load_warnings": config_load_warnings or [],
    }
    if source_layer_manifest_path:
        manifest["source_layer_manifest_path"] = source_layer_manifest_path
    return manifest


def load_target_layer_manifest(layer_name: str, loaded_symbols: list[str], universes_dir: Path = UNIVERSES_DIR) -> dict[str, Any]:
    config_path = universes_dir / f"{layer_name}.yaml"
    warnings: list[str] = []
    data = _read_yaml(config_path, warnings)
    configured = extract_configured_symbols(data)
    universe_name = str(data.get("name") or layer_name) if isinstance(data, dict) else layer_name
    universe_type = str(data.get("universe_type") or _default_universe_type(layer_name)) if isinstance(data, dict) else _default_universe_type(layer_name)
    return build_layer_manifest(
        layer_name=layer_name,
        universe_name=universe_name,
        universe_type=universe_type,
        config_source_path=config_path,
        configured_symbols=configured,
        loaded_symbols=loaded_symbols,
        root_watchlist_layer_name=LAYER_TO_ROOT_MIRROR.get(layer_name),
        config_load_status="ok" if config_path.exists() else "missing",
        config_load_warnings=warnings,
    )


def build_minute_probe_manifest(loaded_symbols: list[str], universes_dir: Path = UNIVERSES_DIR) -> dict[str, Any]:
    core = load_target_layer_manifest("tech_core", [], universes_dir)
    candidates = load_target_layer_manifest("tech_operation_candidates", [], universes_dir)
    configured = list(dict.fromkeys(core["configured_symbols"] + candidates["configured_symbols"]))
    warnings = []
    warnings.extend(f"tech_core: {item}" for item in core.get("config_load_warnings", []))
    warnings.extend(f"tech_operation_candidates: {item}" for item in candidates.get("config_load_warnings", []))
    manifest = build_layer_manifest(
        layer_name="tech_minute_probe",
        universe_name="tech_minute_probe",
        universe_type="minute_probe",
        config_source_path="config/universes/tech_core.yaml+config/universes/tech_operation_candidates.yaml",
        configured_symbols=configured,
        loaded_symbols=loaded_symbols,
        config_load_warnings=warnings,
    )
    manifest["config_source_exists"] = bool(core.get("config_source_exists")) and bool(candidates.get("config_source_exists"))
    manifest["config_source_hash_sha256"] = hashlib.sha256(
        (str(core.get("config_source_hash_sha256", "")) + str(candidates.get("config_source_hash_sha256", ""))).encode("utf-8")
    ).hexdigest()
    manifest["config_source_mtime"] = f"{core.get('config_source_mtime', '')};{candidates.get('config_source_mtime', '')}"
    return manifest


def write_layer_manifest(output_dir: Path, manifest: dict[str, Any], filename: str = "layer_manifest.json") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / filename).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def layer_manifest_from_records(records: list[Any], runtime: dict[str, Any]) -> dict[str, Any] | None:
    loaded_symbols = [str(record.symbol) for record in records]
    universe_name = str(runtime.get("universe_name") or "")
    if universe_name in LAYER_TO_ROOT_MIRROR or universe_name == "tech_core":
        return load_target_layer_manifest(universe_name, loaded_symbols)
    if universe_name == "tech_minute_probe" or runtime.get("include_minute_bars"):
        return build_minute_probe_manifest(loaded_symbols)
    if not runtime.get("registry_enabled") and str(runtime.get("profile")) == "tech":
        return load_target_layer_manifest("tech_core", loaded_symbols)
    return None


def layer_manifest_summary_lines(manifest: dict[str, Any] | None) -> list[str]:
    if not manifest:
        return ["- layer_manifest: not_applicable"]
    lines = [
        f"- layer_name: {manifest.get('layer_name', '')}",
        f"- config_source_path: {manifest.get('config_source_path', '')}",
        f"- config_source_hash_sha256: {str(manifest.get('config_source_hash_sha256', ''))[:12]}",
        f"- configured_symbol_count: {manifest.get('configured_symbol_count', 0)}",
        f"- loaded_symbol_count: {manifest.get('loaded_symbol_count', 0)}",
        f"- config_mismatch: {str(manifest.get('config_mismatch', False)).lower()}",
        f"- missing_from_loaded: {_join_symbols(manifest.get('missing_from_loaded', []))}",
        f"- extra_loaded_symbols: {_join_symbols(manifest.get('extra_loaded_symbols', []))}",
        f"- legacy_fallback_used: {str(manifest.get('legacy_fallback_used', False)).lower()}",
        f"- hardcoded_default_used: {str(manifest.get('hardcoded_default_used', False)).lower()}",
    ]
    if manifest.get("config_mismatch"):
        lines.insert(0, "- CONFIG_MISMATCH: true")
    return lines


def run_config_check(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    root_data = _read_yaml(WATCHLIST_PATH, [])
    registry = _read_yaml(REGISTRY_PATH, [])
    root_layers = root_data.get("projects", {}).get("tech", {}).get("layer_universes", {}) if isinstance(root_data, dict) else {}
    universe_results = {}
    all_symbols: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    for layer in TECH_LAYER_ORDER:
        data_warnings: list[str] = []
        data = _read_yaml(UNIVERSES_DIR / f"{layer}.yaml", data_warnings)
        symbols = extract_configured_symbols(data)
        all_symbols.extend(symbols)
        root_key = LAYER_TO_ROOT_MIRROR[layer]
        root_symbols = extract_configured_symbols(root_data, root_key)
        mirror_matches = symbols == root_symbols
        if not mirror_matches:
            errors.append(f"root_mirror_mismatch:{layer}:{root_key}")
        duplicates = _duplicates(symbols)
        if duplicates:
            errors.append(f"duplicate_symbols:{layer}:{','.join(duplicates)}")
        metadata_warnings = _metadata_symbol_warnings(data, layer)
        warnings.extend(metadata_warnings)
        warnings.extend(data_warnings)
        universe_results[layer] = {
            "root_layer_name": root_key,
            "config_source_path": _display_path(UNIVERSES_DIR / f"{layer}.yaml"),
            "configured_symbol_count": len(symbols),
            "configured_symbols": symbols,
            "duplicate_configured_symbols": duplicates,
            "root_mirror_symbol_count": len(root_symbols),
            "root_mirror_symbols": root_symbols,
            "root_mirror_matches": mirror_matches,
            "config_warnings": data_warnings + metadata_warnings,
        }
    registry_keys = list(registry.keys()) if isinstance(registry, dict) else []
    missing_registry = [symbol for symbol in dict.fromkeys(all_symbols) if symbol not in registry_keys]
    if missing_registry:
        errors.append("missing_registry_symbols:" + ",".join(missing_registry))
    registry_duplicates = _duplicates(registry_keys)
    hard_rule_results = _hard_rule_check(universe_results, registry if isinstance(registry, dict) else {})
    errors.extend(hard_rule_results["errors"])
    warnings.extend(hard_rule_results["warnings"])
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "ok",
        "universes": universe_results,
        "root_watchlist_path": _display_path(WATCHLIST_PATH),
        "root_watchlist_hash_sha256": _sha256(WATCHLIST_PATH),
        "symbol_registry_path": _display_path(REGISTRY_PATH),
        "symbol_registry_hash_sha256": _sha256(REGISTRY_PATH),
        "missing_registry_symbols": missing_registry,
        "duplicate_registry_entries": registry_duplicates,
        "hard_rule_check": hard_rule_results,
        "warnings": warnings,
        "errors": errors,
    }
    (output_dir / "tech_layer_config_check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "tech_layer_config_check.md").write_text(format_config_check_markdown(result), encoding="utf-8")
    return result


def format_config_check_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Tech Layer Config Check",
        "",
        f"- generated_at: {result.get('generated_at', '')}",
        f"- status: {result.get('status', '')}",
        f"- root_watchlist_path: {result.get('root_watchlist_path', '')}",
        f"- symbol_registry_path: {result.get('symbol_registry_path', '')}",
        "",
        "## Count Check",
        "",
        "| layer | root_layer | configured | root_mirror | mirror_matches | duplicates |",
        "|---|---|---:|---:|---|---|",
    ]
    for layer, info in result.get("universes", {}).items():
        lines.append(
            f"| {layer} | {info.get('root_layer_name', '')} | {info.get('configured_symbol_count', 0)} | {info.get('root_mirror_symbol_count', 0)} | {str(info.get('root_mirror_matches', False)).lower()} | {_join_symbols(info.get('duplicate_configured_symbols', []))} |"
        )
    lines.extend(["", "## Symbols"])
    for layer, info in result.get("universes", {}).items():
        lines.append(f"- {layer}: {_join_symbols(info.get('configured_symbols', []))}")
    lines.extend(
        [
            "",
            "## Registry Check",
            f"- missing_registry_symbols: {_join_symbols(result.get('missing_registry_symbols', []))}",
            f"- duplicate_registry_entries: {_join_symbols(result.get('duplicate_registry_entries', []))}",
            "",
            "## Hard Rule Check",
        ]
    )
    hard = result.get("hard_rule_check", {})
    for item in hard.get("checks", []):
        lines.append(f"- {item.get('name', '')}: {item.get('status', '')} ({item.get('detail', '')})")
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {warning}" for warning in result.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Errors"])
    lines.extend([f"- {error}" for error in result.get("errors", [])] or ["- none"])
    return "\n".join(lines) + "\n"


def _symbols_from_value(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    symbols: list[str] = []
    for item in value:
        if isinstance(item, str):
            symbol = item.strip()
        elif isinstance(item, dict) and "symbol" in item:
            symbol = str(item.get("symbol", "")).strip()
        else:
            symbol = ""
        if symbol:
            symbols.append(symbol)
    return symbols


def _read_yaml(path: Path, warnings: list[str]) -> Any:
    if not path.exists():
        warnings.append(f"missing_config:{_display_path(path)}")
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        warnings.append(f"yaml_load_error:{_display_path(path)}:{type(exc).__name__}:{exc}")
        return {}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _duplicates(symbols: list[str]) -> list[str]:
    seen: set[str] = set()
    dupes: list[str] = []
    for symbol in symbols:
        if symbol in seen and symbol not in dupes:
            dupes.append(symbol)
        seen.add(symbol)
    return dupes


def _join_symbols(symbols: Any) -> str:
    if not symbols:
        return "none"
    return ", ".join(str(symbol) for symbol in symbols)


def _default_universe_type(layer_name: str) -> str:
    return {
        "tech_core": "core_holdings",
        "tech_operation_candidates": "operation_candidate",
        "tech_watchlist": "candidate_watchlist",
        "tech_scan_ai": "scan_universe",
    }.get(layer_name, "")


def _metadata_symbol_warnings(data: Any, layer: str) -> list[str]:
    warnings: list[str] = []
    if not isinstance(data, dict):
        return warnings
    for key in FORBIDDEN_METADATA_KEYS:
        if _contains_symbol_key(data.get(key)):
            warnings.append(f"{layer}:{key} metadata contains symbol keys; ensure loaders only read top-level symbols.")
    return warnings


def _contains_symbol_key(value: Any) -> bool:
    if isinstance(value, dict):
        if "symbol" in value:
            return True
        return any(_contains_symbol_key(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_symbol_key(item) for item in value)
    return False


def _hard_rule_check(universe_results: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    candidates = universe_results.get("tech_operation_candidates", {}).get("configured_symbols", [])
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, str]] = []

    def add(name: str, ok: bool, detail: str, *, warning: bool = False) -> None:
        checks.append({"name": name, "status": "ok" if ok else ("warning" if warning else "failed"), "detail": detail})
        if not ok and warning:
            warnings.append(f"{name}:{detail}")
        elif not ok:
            errors.append(f"{name}:{detail}")

    add(
        "002463_not_operation_candidate",
        "002463.SZ" not in candidates,
        "002463.SZ not present" if "002463.SZ" not in candidates else "002463.SZ present in operation_candidate",
    )
    add(
        "GOLD_CNY_not_operation_candidate",
        "GOLD_CNY" not in candidates,
        "GOLD_CNY not present" if "GOLD_CNY" not in candidates else "GOLD_CNY present in operation_candidate",
    )
    add(
        "510300_not_operation_candidate",
        "510300.SH" not in candidates,
        "510300.SH not present" if "510300.SH" not in candidates else "510300.SH present in operation_candidate",
    )
    if "159516.SZ" in candidates:
        text = " ".join(
            [
                str(registry.get("159516.SZ", {}).get("notes", "")),
                str(registry.get("159516.SZ", {}).get("candidate_restriction", "")),
            ]
        ).lower()
        required = ["failed", "no_add_no_t", "not_repair_candidate", "re_evaluation"]
        ok = all(marker in text for marker in required)
        add("159516_candidate_restriction", ok, "159516.SZ restriction markers required")
    else:
        add("159516_candidate_restriction", True, "159516.SZ not present in operation_candidate")
    add("scan_watchlist_not_auto_operation", True, "reported only; script does not modify config")
    return {"checks": checks, "warnings": warnings, "errors": errors}
