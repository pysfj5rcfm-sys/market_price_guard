from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import Instrument, WatchProject, Watchlist


CORE_HOLDINGS = "core_holdings"
CANDIDATE_WATCHLIST = "candidate_watchlist"
SCAN_UNIVERSE = "scan_universe"
CONTROLLER_SUMMARY = "controller_summary"
OPERATION_CANDIDATE = "operation_candidate"


@dataclass(frozen=True)
class UniverseSpec:
    name: str
    profile: str
    universe_type: str
    quote_purpose: str
    symbols: list[str]


def load_symbol_registry(path: Path) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return {str(key): dict(value or {}) for key, value in data.items()}


def load_universe(name_or_path: str, universes_dir: Path) -> UniverseSpec:
    path = Path(name_or_path)
    if not path.suffix:
        path = universes_dir / f"{name_or_path}.yaml"
    if not path.is_absolute():
        path = universes_dir / path
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return UniverseSpec(
        name=str(data.get("name") or path.stem),
        profile=str(data.get("profile") or "all"),
        universe_type=str(data.get("universe_type") or SCAN_UNIVERSE),
        quote_purpose=str(data.get("quote_purpose") or "reference"),
        symbols=[str(symbol).strip() for symbol in data.get("symbols", []) if str(symbol).strip()],
    )


def build_watchlist_from_registry(
    registry_path: Path,
    universes_dir: Path,
    profile: str,
    quote_purpose: str,
    universe: str | None = None,
    symbols: str | None = None,
    symbol_file: Path | None = None,
    include_watchlist: bool = False,
    include_candidates: bool = False,
    universe_type: str | None = None,
) -> tuple[Watchlist, dict[str, Any]]:
    registry = load_symbol_registry(registry_path)
    spec = _resolve_universe_spec(
        universes_dir=universes_dir,
        profile=profile,
        quote_purpose=quote_purpose,
        universe=universe,
        symbols=symbols,
        symbol_file=symbol_file,
        universe_type=universe_type,
    )
    resolved_symbols = list(spec.symbols)
    if include_watchlist or include_candidates:
        resolved_symbols.extend(_extra_candidate_symbols(profile, universes_dir))
    resolved_symbols = list(dict.fromkeys(resolved_symbols))

    projects: dict[str, WatchProject] = {}
    unsupported: list[dict[str, str]] = []
    for symbol in resolved_symbols:
        entry = _registry_entry(symbol, registry, spec)
        if not entry["registry_found"] or entry.get("unsupported_reason"):
            unsupported.append(
                {
                    "symbol": symbol,
                    "inferred_market": str(entry.get("market", "")),
                    "registry_found": str(entry["registry_found"]).lower(),
                    "asset_type": str(entry.get("asset_type", "unknown")),
                    "universe_type": str(entry.get("universe_type", spec.universe_type)),
                    "reason": str(entry.get("unsupported_reason") or "not_registered"),
                    "suggested_fix": "add this symbol to config/symbol_registry.yaml or fix symbol format",
                }
            )
        project_key = _project_key(entry, spec.profile)
        project = projects.setdefault(
            project_key,
            WatchProject(display_name=project_key, allow_full_detail=project_key != "controller", instruments=[]),
        )
        project.instruments.append(_instrument_from_entry(entry, spec, quote_purpose))

    metadata = {
        "registry_enabled": True,
        "registry_path": str(registry_path),
        "universe_name": spec.name,
        "universe_type": spec.universe_type,
        "universe_quote_purpose": spec.quote_purpose,
        "universe_symbols": resolved_symbols,
        "unsupported_symbols": unsupported,
        "core_count": sum(1 for project in projects.values() for item in project.instruments if item.universe_type == CORE_HOLDINGS),
        "watchlist_count": sum(1 for project in projects.values() for item in project.instruments if item.universe_type == CANDIDATE_WATCHLIST),
        "scan_count": sum(1 for project in projects.values() for item in project.instruments if item.universe_type == SCAN_UNIVERSE),
        "operation_candidate_count": sum(1 for project in projects.values() for item in project.instruments if item.universe_type == OPERATION_CANDIDATE),
        "unsupported_count": len(unsupported),
    }
    return Watchlist(projects=projects), metadata


def merge_watchlist_with_registry(watchlist: Watchlist, registry_path: Path) -> Watchlist:
    registry = load_symbol_registry(registry_path)
    projects: dict[str, WatchProject] = {}
    for project_key, project in watchlist.projects.items():
        instruments: list[Instrument] = []
        for instrument in project.instruments:
            entry = registry.get(instrument.symbol)
            if entry is None:
                instruments.append(instrument)
                continue
            instruments.append(_merge_instrument_metadata(instrument, dict(entry), project_key))
        projects[project_key] = WatchProject(
            display_name=project.display_name,
            allow_full_detail=project.allow_full_detail,
            instruments=instruments,
        )
    return Watchlist(projects=projects)


def _resolve_universe_spec(
    universes_dir: Path,
    profile: str,
    quote_purpose: str,
    universe: str | None,
    symbols: str | None,
    symbol_file: Path | None,
    universe_type: str | None,
) -> UniverseSpec:
    if symbols:
        return UniverseSpec(
            name="cli_symbols",
            profile=profile,
            universe_type=universe_type or SCAN_UNIVERSE,
            quote_purpose=quote_purpose or "reference",
            symbols=_split_symbols(symbols),
        )
    if symbol_file:
        return UniverseSpec(
            name=symbol_file.stem,
            profile=profile,
            universe_type=universe_type or SCAN_UNIVERSE,
            quote_purpose=quote_purpose or "reference",
            symbols=_load_symbol_file(symbol_file),
        )
    if universe:
        spec = load_universe(universe, universes_dir)
        if universe_type:
            spec = UniverseSpec(spec.name, spec.profile, universe_type, spec.quote_purpose, spec.symbols)
        return spec
    default_name = {
        "tech": "tech_core",
        "energy": "energy_core",
        "all": "controller_core",
        "controller": "controller_core",
    }.get(profile, "controller_core")
    return load_universe(default_name, universes_dir)


def _split_symbols(symbols: str) -> list[str]:
    return [symbol.strip() for symbol in symbols.split(",") if symbol.strip()]


def _load_symbol_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text) or {}
        if isinstance(data, dict):
            raw_symbols = data.get("symbols", [])
        else:
            raw_symbols = data
        return [str(symbol).strip() for symbol in raw_symbols if str(symbol).strip()]
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]


def _extra_candidate_symbols(profile: str, universes_dir: Path) -> list[str]:
    name = f"{profile}_watchlist"
    path = universes_dir / f"{name}.yaml"
    if not path.exists():
        return []
    return load_universe(name, universes_dir).symbols


def _registry_entry(symbol: str, registry: dict[str, dict[str, Any]], spec: UniverseSpec) -> dict[str, Any]:
    if symbol in registry:
        entry = dict(registry[symbol])
        entry.setdefault("symbol", symbol)
        entry.setdefault("universe_type", spec.universe_type)
        entry.setdefault("registry_found", True)
        entry.setdefault("unsupported_reason", "")
        return entry
    market = _infer_market(symbol)
    return {
        "symbol": symbol,
        "name": symbol,
        "market": market or "UNKNOWN",
        "asset_type": "unknown",
        "project_scope": spec.profile if spec.profile != "all" else "controller",
        "role": "unsupported_symbol",
        "universe_tags": ["unsupported"],
        "required_for_operation": False,
        "default_quote_purpose": "reference",
        "provider_preference": {"reference": ["mock"], "operation": ["mock"], "reconcile": ["mock"]},
        "report_group": "unsupported_symbols",
        "enabled": True,
        "notes": "",
        "registry_found": False,
        "unsupported_reason": "not_registered" if market else "invalid_symbol_format",
        "universe_type": spec.universe_type,
    }


def _infer_market(symbol: str) -> str:
    if symbol.endswith(".SH"):
        return "SH"
    if symbol.endswith(".SZ"):
        return "SZ"
    if symbol.endswith(".HK"):
        return "HK"
    if "_" in symbol:
        return "MANUAL"
    return ""


def _project_key(entry: dict[str, Any], profile: str) -> str:
    scope = str(entry.get("project_scope") or profile or "controller")
    if scope in {"all", "controller_summary"}:
        return "controller"
    return scope


def _instrument_from_entry(entry: dict[str, Any], spec: UniverseSpec, quote_purpose: str) -> Instrument:
    provider_priority = _provider_priority(entry, spec, quote_purpose)
    provider = provider_priority[0] if provider_priority else "mock"
    universe_type = str(entry.get("universe_type") or spec.universe_type)
    required = bool(entry.get("required_for_operation", False)) and universe_type == CORE_HOLDINGS
    operation_candidate = universe_type == OPERATION_CANDIDATE or bool(entry.get("operation_candidate", False))
    affect_core_strict = bool(entry.get("affect_core_strict", universe_type == CORE_HOLDINGS))
    if operation_candidate:
        affect_core_strict = False
    return Instrument(
        symbol=str(entry.get("symbol")),
        name=str(entry.get("name") or entry.get("symbol")),
        market=_market_for_model(str(entry.get("market") or "")),
        core=universe_type == CORE_HOLDINGS,
        provider=provider,
        provider_priority=provider_priority,
        required_for_operation=required,
        asset_role=str(entry.get("role") or ""),
        asset_type=str(entry.get("asset_type") or ""),
        project_scope=str(entry.get("project_scope") or spec.profile),
        role=str(entry.get("role") or ""),
        universe_tags=[str(tag) for tag in entry.get("universe_tags", [])],
        universe_type=universe_type,
        default_quote_purpose=spec.quote_purpose
        if universe_type in {CANDIDATE_WATCHLIST, SCAN_UNIVERSE, OPERATION_CANDIDATE}
        else str(entry.get("default_quote_purpose") or spec.quote_purpose),
        report_group=str(entry.get("report_group") or ""),
        notes=str(entry.get("notes") or ""),
        registry_found=bool(entry.get("registry_found", True)),
        unsupported_reason=str(entry.get("unsupported_reason") or ""),
        affect_core_strict=affect_core_strict,
        operation_candidate=operation_candidate,
        source_universe=spec.name,
    )


def _merge_instrument_metadata(instrument: Instrument, entry: dict[str, Any], project_key: str) -> Instrument:
    data = instrument.model_dump()
    data["asset_type"] = data.get("asset_type") or str(entry.get("asset_type") or "")
    data["project_scope"] = data.get("project_scope") or str(entry.get("project_scope") or project_key)
    data["role"] = data.get("role") or str(entry.get("role") or data.get("asset_role") or "")
    data["asset_role"] = data.get("asset_role") or str(entry.get("role") or "")
    data["universe_tags"] = data.get("universe_tags") or [str(tag) for tag in entry.get("universe_tags", [])]
    data["universe_type"] = data.get("universe_type") or _default_universe_type_for_project(project_key)
    data["default_quote_purpose"] = data.get("default_quote_purpose") or str(entry.get("default_quote_purpose") or "")
    data["report_group"] = data.get("report_group") or str(entry.get("report_group") or "")
    data["notes"] = data.get("notes") or str(entry.get("notes") or "")
    data["registry_found"] = True
    data["unsupported_reason"] = data.get("unsupported_reason") or ""
    data["source_universe"] = data.get("source_universe") or _default_source_universe_for_project(project_key, data.get("universe_type") or "")
    return Instrument(**data)


def _default_universe_type_for_project(project_key: str) -> str:
    if project_key == "controller":
        return CONTROLLER_SUMMARY
    return CORE_HOLDINGS


def _default_source_universe_for_project(project_key: str, universe_type: str) -> str:
    if universe_type == OPERATION_CANDIDATE:
        return f"{project_key}_operation_candidates"
    if universe_type == CANDIDATE_WATCHLIST:
        return f"{project_key}_watchlist"
    if universe_type == SCAN_UNIVERSE:
        return f"{project_key}_scan"
    if universe_type == CONTROLLER_SUMMARY:
        return "controller_core"
    return f"{project_key}_core"


def _provider_priority(entry: dict[str, Any], spec: UniverseSpec, quote_purpose: str) -> list[str]:
    preferences = entry.get("provider_preference") or {}
    purpose = "reconcile" if spec.name.endswith("reconcile") else quote_purpose
    if isinstance(preferences, dict):
        priority = preferences.get(purpose) or preferences.get(spec.quote_purpose) or preferences.get("reference") or preferences.get("operation")
    else:
        priority = preferences
    if not priority:
        return ["mock"]
    return [str(provider) for provider in priority]


def _market_for_model(market: str) -> str:
    if market in {"SH", "SZ", "CN"}:
        return "CN"
    return market or "UNKNOWN"
