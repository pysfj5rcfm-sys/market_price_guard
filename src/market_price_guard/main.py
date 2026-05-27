from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .normalize import load_watchlist, load_yaml, normalize_records
from .price_reconciliation import apply_reconciliation
from .provider_router import ProviderRuntimeBudget, RouterConfig, collect_routed_prices
from .quote_run_cache import load_manifest as load_quote_cache_manifest
from .models import WatchProject, Watchlist
from .minute_bars import apply_minute_bars_probe
from .providers.akshare_provider import AkshareProvider
from .providers.eastmoney_direct_provider import EastmoneyDirectProvider
from .providers.manual_provider import ManualProvider
from .providers.mock_provider import MockProvider
from .providers.yfinance_provider import YFinanceProvider
from .report import CompletenessSummary, build_completeness_summary, format_blocking_record, write_outputs
from .scan_ranking import apply_scan_ranking
from .symbol_registry import build_watchlist_from_registry, merge_watchlist_with_registry
from .yfinance_circuit import YFinanceCircuitBreaker
from .config_observability import layer_manifest_from_records, write_layer_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
MANUAL_PRICES_PATH = CONFIG_DIR / "manual_prices.yaml"
SYMBOL_REGISTRY_PATH = CONFIG_DIR / "symbol_registry.yaml"
UNIVERSES_DIR = CONFIG_DIR / "universes"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_STRICT_BLOCKED = 2


@dataclass(frozen=True)
class PipelineResult:
    records_count: int
    output_dir: Path
    strict: bool
    completeness: CompletenessSummary
    exit_code: int
    runtime: dict


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate price freshness reports from mock/manual data.")
    parser.add_argument("--watchlist", type=Path, default=CONFIG_DIR / "watchlist.yaml")
    parser.add_argument("--stale-rules", type=Path, default=CONFIG_DIR / "stale_rules.yaml")
    parser.add_argument("--mock-prices", type=Path, default=CONFIG_DIR / "mock_prices.yaml")
    parser.add_argument("--manual-prices", type=Path, default=MANUAL_PRICES_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--provider-mode", choices=["mock", "live"], default="mock")
    parser.add_argument("--provider-policy", choices=["fast", "conservative", "diagnostic"], default="fast")
    parser.add_argument("--quote-purpose", choices=["operation", "reference"], default="operation")
    parser.add_argument("--reconcile-mode", choices=["default", "full"], default="default")
    parser.add_argument("--include-minute-bars", "--minute-bars-probe", dest="include_minute_bars", action="store_true")
    parser.add_argument("--scan-mode", choices=["fast", "diagnostic"], default="fast")
    parser.add_argument("--minute-mode", choices=["fast", "balanced", "diagnostic"], default="balanced")
    parser.add_argument("--minute-workers", type=int, default=3)
    parser.add_argument("--universe")
    parser.add_argument("--symbols")
    parser.add_argument("--symbol-file", type=Path)
    parser.add_argument("--include-watchlist", action="store_true")
    parser.add_argument("--include-candidates", action="store_true")
    parser.add_argument(
        "--universe-type",
        choices=["core_holdings", "candidate_watchlist", "scan_universe", "operation_candidate", "controller_summary"],
    )
    parser.add_argument("--profile", choices=["all", "energy", "tech", "controller"], default="all")
    parser.add_argument("--timeout-seconds", type=float, default=8.0)
    parser.add_argument("--max-run-seconds", type=float, default=30.0)
    parser.add_argument("--max-data-lag-seconds", type=float, default=300.0)
    parser.add_argument("--strict", action="store_true", help="Return exit code 2 when required price data is unusable.")
    return parser.parse_args(argv)


def collect_prices(
    watchlist_path: Path,
    mock_prices_path: Path,
    manual_prices_path: Path,
    provider_mode: str = "mock",
    profile: str = "all",
    timeout_seconds: float = 8.0,
    provider_policy: str = "fast",
    quote_purpose: str = "operation",
    reconcile_mode: str = "default",
    universe: str | None = None,
    symbols: str | None = None,
    symbol_file: Path | None = None,
    include_watchlist: bool = False,
    include_candidates: bool = False,
    universe_type: str | None = None,
    include_minute_bars: bool = False,
    scan_mode: str = "fast",
    yfinance_circuit: YFinanceCircuitBreaker | None = None,
    runtime_budget: ProviderRuntimeBudget | None = None,
) -> dict:
    registry_enabled = bool(universe or symbols or symbol_file or include_watchlist or include_candidates or universe_type)
    universe_metadata: dict = {}
    if include_minute_bars and profile == "tech" and not registry_enabled:
        watchlist, universe_metadata = _build_tech_minute_probe_watchlist(quote_purpose)
    elif registry_enabled:
        watchlist, universe_metadata = build_watchlist_from_registry(
            registry_path=SYMBOL_REGISTRY_PATH,
            universes_dir=UNIVERSES_DIR,
            profile=profile,
            quote_purpose=quote_purpose,
            universe=universe,
            symbols=symbols,
            symbol_file=symbol_file,
            include_watchlist=include_watchlist,
            include_candidates=include_candidates,
            universe_type=universe_type,
        )
    else:
        watchlist = merge_watchlist_with_registry(_filter_watchlist(load_watchlist(watchlist_path), profile), SYMBOL_REGISTRY_PATH)
    providers = {
        "mock": MockProvider(mock_prices_path),
        "manual": ManualProvider(manual_prices_path),
        "akshare": AkshareProvider(),
        "eastmoney_direct": EastmoneyDirectProvider(),
        "yfinance": YFinanceProvider(),
    }
    prices = collect_routed_prices(
        watchlist,
        providers,
        RouterConfig(
            provider_mode=provider_mode,
            provider_policy=provider_policy,
            timeout_seconds=timeout_seconds,
            quote_purpose=quote_purpose,
            reconcile_mode=reconcile_mode,
            scan_mode=scan_mode,
            yfinance_circuit=yfinance_circuit,
            runtime_budget=runtime_budget,
            account=profile,
            layer=str(universe_metadata.get("universe_name", universe or profile)),
            runtime_profile=scan_mode if quote_purpose == "reference" else provider_policy,
        ),
    )
    return {"watchlist": watchlist, "prices": prices, "universe_metadata": universe_metadata}


def run_pipeline(
    watchlist_path: Path = CONFIG_DIR / "watchlist.yaml",
    stale_rules_path: Path = CONFIG_DIR / "stale_rules.yaml",
    mock_prices_path: Path = CONFIG_DIR / "mock_prices.yaml",
    manual_prices_path: Path = MANUAL_PRICES_PATH,
    output_dir: Path = OUTPUT_DIR,
    provider_mode: str = "mock",
    strict: bool = False,
    profile: str = "all",
    timeout_seconds: float = 8.0,
    provider_policy: str = "fast",
    quote_purpose: str = "operation",
    reconcile_mode: str = "default",
    universe: str | None = None,
    symbols: str | None = None,
    symbol_file: Path | None = None,
    include_watchlist: bool = False,
    include_candidates: bool = False,
    universe_type: str | None = None,
    max_run_seconds: float = 30.0,
    max_data_lag_seconds: float = 300.0,
    include_minute_bars: bool = False,
    scan_mode: str = "fast",
    minute_mode: str = "balanced",
    minute_workers: int = 3,
) -> PipelineResult:
    perf_start = time.perf_counter()
    run_start = _utc_now_iso()
    yfinance_circuit = YFinanceCircuitBreaker()
    provider_runtime_budget = ProviderRuntimeBudget(
        account=profile,
        run_id=run_start,
        timeout_seconds=timeout_seconds,
    )
    collected = collect_prices(
        watchlist_path,
        mock_prices_path,
        manual_prices_path,
        provider_mode,
        profile,
        timeout_seconds,
        provider_policy,
        quote_purpose,
        reconcile_mode,
        universe,
        symbols,
        symbol_file,
        include_watchlist,
        include_candidates,
        universe_type,
        include_minute_bars,
        scan_mode,
        yfinance_circuit,
        provider_runtime_budget,
    )
    rules = load_yaml(stale_rules_path)
    records = apply_scan_ranking(apply_reconciliation(normalize_records(collected["watchlist"], collected["prices"], rules)))
    records = _apply_runtime_mode_fields(records, scan_mode=scan_mode)
    records, minute_bars_snapshot = apply_minute_bars_probe(
        records,
        include_minute_bars=include_minute_bars,
        provider_mode=provider_mode,
        minute_mode=minute_mode,
        minute_workers=minute_workers,
        yfinance_circuit=yfinance_circuit,
    )
    records = _apply_yfinance_circuit_fields(records, yfinance_circuit)
    elapsed = time.perf_counter() - perf_start
    runtime = _runtime_diagnostics(
        records=records,
        run_start_time_utc=run_start,
        total_elapsed_seconds=elapsed,
        profile=profile,
        provider_mode=provider_mode,
        provider_policy=provider_policy,
        quote_purpose=quote_purpose,
        reconcile_mode=reconcile_mode,
        strict=strict,
        max_run_seconds=max_run_seconds,
        max_data_lag_seconds=max_data_lag_seconds,
        include_minute_bars=include_minute_bars,
        scan_mode=scan_mode,
        minute_mode=minute_mode,
        minute_workers=minute_workers,
        yfinance_circuit=yfinance_circuit,
        provider_runtime_budget=provider_runtime_budget,
    )
    runtime["quote_run_cache"] = load_quote_cache_manifest()
    completeness = build_completeness_summary(records)
    exit_code = EXIT_STRICT_BLOCKED if strict and not completeness.usable_for_operation else EXIT_OK
    runtime["exit_code"] = exit_code
    runtime["minute_bars_snapshot"] = minute_bars_snapshot
    runtime.update(yfinance_circuit.snapshot())
    runtime.update(collected.get("universe_metadata", {}))
    layer_manifest = layer_manifest_from_records(records, runtime)
    if layer_manifest:
        runtime["layer_manifest"] = layer_manifest
    write_outputs(records, output_dir, provider_mode=provider_mode, runtime=runtime)
    if layer_manifest:
        write_layer_manifest(output_dir, layer_manifest)
    return PipelineResult(
        records_count=len(records),
        output_dir=output_dir,
        strict=strict,
        completeness=completeness,
        exit_code=exit_code,
        runtime=runtime,
    )


def _build_tech_minute_probe_watchlist(quote_purpose: str) -> tuple[Watchlist, dict]:
    core_watchlist, core_metadata = build_watchlist_from_registry(
        registry_path=SYMBOL_REGISTRY_PATH,
        universes_dir=UNIVERSES_DIR,
        profile="tech",
        quote_purpose=quote_purpose,
        universe="tech_core",
    )
    candidate_watchlist, candidate_metadata = build_watchlist_from_registry(
        registry_path=SYMBOL_REGISTRY_PATH,
        universes_dir=UNIVERSES_DIR,
        profile="tech",
        quote_purpose="reference",
        universe="tech_operation_candidates",
    )
    merged = _merge_watchlists_core_first(core_watchlist, candidate_watchlist)
    instruments = [instrument for project in merged.projects.values() for instrument in project.instruments]
    metadata = {
        "registry_enabled": True,
        "registry_path": str(SYMBOL_REGISTRY_PATH),
        "universe_name": "tech_minute_probe",
        "universe_type": "minute_probe",
        "universe_quote_purpose": "reference",
        "universe_symbols": [instrument.symbol for instrument in instruments],
        "unsupported_symbols": [
            *core_metadata.get("unsupported_symbols", []),
            *candidate_metadata.get("unsupported_symbols", []),
        ],
        "core_count": sum(1 for instrument in instruments if instrument.source_universe == "tech_core"),
        "watchlist_count": 0,
        "scan_count": 0,
        "operation_candidate_count": sum(1 for instrument in instruments if instrument.source_universe == "tech_operation_candidates"),
        "unsupported_count": len(core_metadata.get("unsupported_symbols", [])) + len(candidate_metadata.get("unsupported_symbols", [])),
    }
    return merged, metadata


def _merge_watchlists_core_first(core_watchlist: Watchlist, candidate_watchlist: Watchlist) -> Watchlist:
    projects: dict[str, WatchProject] = {}
    seen: set[str] = set()
    for watchlist in (core_watchlist, candidate_watchlist):
        for project_key, project in watchlist.projects.items():
            merged_project = projects.setdefault(
                project_key,
                WatchProject(display_name=project.display_name, allow_full_detail=project.allow_full_detail, instruments=[]),
            )
            for instrument in project.instruments:
                if instrument.symbol in seen:
                    continue
                seen.add(instrument.symbol)
                merged_project.instruments.append(instrument)
    return Watchlist(projects=projects)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run_pipeline(
            watchlist_path=args.watchlist,
            stale_rules_path=args.stale_rules,
            mock_prices_path=args.mock_prices,
            manual_prices_path=args.manual_prices,
            output_dir=args.output_dir,
            provider_mode=args.provider_mode,
            provider_policy=args.provider_policy,
            quote_purpose=args.quote_purpose,
            reconcile_mode=args.reconcile_mode,
            universe=args.universe,
            symbols=args.symbols,
            symbol_file=args.symbol_file,
            include_watchlist=args.include_watchlist,
            include_candidates=args.include_candidates,
            universe_type=args.universe_type,
            strict=args.strict,
            profile=args.profile,
            timeout_seconds=args.timeout_seconds,
            max_run_seconds=args.max_run_seconds,
            max_data_lag_seconds=args.max_data_lag_seconds,
            include_minute_bars=args.include_minute_bars,
            scan_mode=args.scan_mode,
            minute_mode=args.minute_mode,
            minute_workers=args.minute_workers,
        )
    except Exception as exc:
        print(f"market_price_guard failed: {exc}", file=sys.stderr)
        return EXIT_ERROR

    print(f"Generated {result.records_count} price records in {result.output_dir}")
    if result.exit_code == EXIT_STRICT_BLOCKED:
        print(
            "Strict mode blocked operation because the following required prices are not usable:",
            file=sys.stderr,
        )
        for record in result.completeness.strict_blockers:
            print(format_blocking_record(record), file=sys.stderr)
    else:
        print("Price guard completed without strict blocking records.")
    return result.exit_code


def _filter_watchlist(watchlist: Watchlist, profile: str) -> Watchlist:
    if profile == "all":
        return watchlist
    if profile in watchlist.projects:
        project = watchlist.projects[profile]
        return Watchlist(projects={profile: WatchProject(**project.model_dump())})
    return Watchlist(projects={})


def _runtime_diagnostics(
    records,
    run_start_time_utc: str,
    total_elapsed_seconds: float,
    profile: str,
    provider_mode: str,
    provider_policy: str,
    quote_purpose: str,
    reconcile_mode: str,
    strict: bool,
    max_run_seconds: float,
    max_data_lag_seconds: float,
    include_minute_bars: bool,
    scan_mode: str,
    minute_mode: str,
    minute_workers: int,
    yfinance_circuit: YFinanceCircuitBreaker | None = None,
    provider_runtime_budget: ProviderRuntimeBudget | None = None,
) -> dict:
    from datetime import datetime, timezone

    run_end = datetime.now(timezone.utc)
    quote_times = [record.quote_time.astimezone(timezone.utc) for record in records if record.quote_time is not None]
    quote_lags = [(run_end - quote_time).total_seconds() for quote_time in quote_times]
    max_quote_lag = max(quote_lags) if quote_lags else None
    return {
        "run_start_time_utc": run_start_time_utc,
        "run_end_time_utc": run_end.isoformat(),
        "total_elapsed_seconds": round(total_elapsed_seconds, 3),
        "profile": profile,
        "provider_mode": provider_mode,
        "provider_policy": provider_policy,
        "strict": strict,
        "quote_purpose": quote_purpose,
        "reconcile_mode": reconcile_mode,
        "include_minute_bars": include_minute_bars,
        "scan_mode": scan_mode,
        "minute_mode": minute_mode,
        "minute_workers": minute_workers,
        "parallel_enabled": False,
        "parallel_note": "workers parameter parsed, execution remains serial in this version",
        "timeout_seconds": "",
        "future_quote_tolerance_seconds": 120,
        **((yfinance_circuit.snapshot()) if yfinance_circuit else {}),
        "max_run_seconds": max_run_seconds,
        "max_data_lag_seconds": max_data_lag_seconds,
        "run_time_budget_exceeded": total_elapsed_seconds > max_run_seconds,
        "max_quote_lag_seconds": "" if max_quote_lag is None else round(max_quote_lag, 3),
        "provider_elapsed_seconds": dict(provider_runtime_budget.elapsed_by_provider) if provider_runtime_budget else {},
        "provider_attempts": dict(provider_runtime_budget.attempts_by_provider) if provider_runtime_budget else {},
        "provider_slow_attempts": dict(provider_runtime_budget.slow_attempts_by_provider) if provider_runtime_budget else {},
        "provider_failed_attempts": dict(provider_runtime_budget.failed_attempts_by_provider) if provider_runtime_budget else {},
        "provider_timeout_attempts": dict(provider_runtime_budget.timeout_attempts_by_provider) if provider_runtime_budget else {},
        "provider_skipped_by_budget": dict(provider_runtime_budget.skipped_by_budget_by_provider) if provider_runtime_budget else {},
        "provider_circuit_open": dict(provider_runtime_budget.circuit_open_by_provider) if provider_runtime_budget else {},
        "provider_budget_account": provider_runtime_budget.account if provider_runtime_budget else profile,
        "provider_budget_run_id": provider_runtime_budget.run_id if provider_runtime_budget else run_start_time_utc,
        "provider_max_attempts": dict(provider_runtime_budget.max_attempts_by_provider) if provider_runtime_budget else {},
        "provider_max_time_seconds": dict(provider_runtime_budget.max_time_seconds_by_provider) if provider_runtime_budget else {},
        "quote_cache_hit_count": sum(1 for record in records if record.provider_diagnostics.get("cache_hit")),
        "quote_cache_miss_count": sum(1 for record in records if record.provider_diagnostics.get("cache_miss")),
        "quote_cache_success_hit_count": sum(1 for record in records if record.provider_diagnostics.get("cache_hit") and record.price is not None),
        "quote_cache_failure_hit_count": sum(1 for record in records if record.provider_diagnostics.get("cache_hit") and record.price is None),
        "repeated_provider_call_prevented_count": sum(1 for record in records if record.provider_diagnostics.get("repeated_provider_call_prevented")),
    }


def _apply_runtime_mode_fields(records, scan_mode: str):
    updated = []
    for record in records:
        attempts = record.provider_diagnostics.get("provider_attempts", []) or []
        providers_attempted = [
            str(attempt.get("provider", ""))
            for attempt in attempts
            if isinstance(attempt, dict) and str(attempt.get("provider", ""))
        ]
        provider_attempted = ",".join(dict.fromkeys(providers_attempted))
        provider_success = any(isinstance(attempt, dict) and attempt.get("status") == "success" for attempt in attempts)
        provider_timeout = "provider_timeout" in record.quality_issues or any(
            isinstance(attempt, dict) and (attempt.get("reason") == "provider_timeout" or attempt.get("slow_provider_attempt"))
            for attempt in attempts
        )
        stock_fast = (
            scan_mode == "fast"
            and record.universe_type == "scan_universe"
            and record.asset_type.lower() == "stock"
            and record.symbol.endswith((".SH", ".SZ"))
        )
        update = {
            "scan_mode": scan_mode if record.universe_type == "scan_universe" else "",
            "stock_fast_path_enabled": stock_fast,
            "stock_fast_provider": "eastmoney_direct" if stock_fast else "",
            "provider_timeout": bool(provider_timeout),
            "fallback_skipped_fast_mode": bool(stock_fast and "akshare" not in providers_attempted),
            "provider_attempted": provider_attempted,
            "base_quote_provider_attempted": provider_attempted,
            "yfinance_fallback_policy": _yfinance_fallback_policy(record, scan_mode),
            "fallback_skipped_yfinance_circuit_open": any(
                isinstance(attempt, dict) and attempt.get("reason") == "fallback_skipped_yfinance_circuit_open"
                for attempt in attempts
            ),
            "provider_success": bool(provider_success),
        }
        if stock_fast:
            diagnostics = dict(record.provider_diagnostics)
            diagnostics.update(
                {
                    "scan_mode": scan_mode,
                    "stock_fast_path_enabled": True,
                    "stock_fast_provider": "eastmoney_direct",
                    "fallback_skipped_fast_mode": update["fallback_skipped_fast_mode"],
                }
            )
            update["provider_diagnostics"] = diagnostics
        updated.append(record.model_copy(update=update))
    return updated


def _yfinance_fallback_policy(record, scan_mode: str) -> str:
    if record.universe_type == "scan_universe":
        if scan_mode == "fast" and record.asset_type.lower() == "stock" and record.symbol.endswith((".SH", ".SZ")):
            return "disabled_in_fast_mode"
        if scan_mode == "diagnostic":
            return "enabled_with_circuit_breaker"
    return ""


def _apply_yfinance_circuit_fields(records, yfinance_circuit: YFinanceCircuitBreaker):
    snapshot = yfinance_circuit.snapshot()
    updated = []
    for record in records:
        update = {
            "yfinance_circuit_open": bool(snapshot.get("yfinance_circuit_open")),
            "yfinance_circuit_reason": str(snapshot.get("yfinance_circuit_reason") or ""),
        }
        if record.yfinance_fallback_policy == "" and record.minute_mode:
            if record.minute_mode == "fast":
                update["yfinance_fallback_policy"] = "disabled_in_fast_mode"
            elif record.minute_mode == "balanced":
                update["yfinance_fallback_policy"] = "enabled_until_circuit_open"
            elif record.minute_mode == "diagnostic":
                update["yfinance_fallback_policy"] = "enabled_with_circuit_breaker"
        updated.append(record.model_copy(update=update))
    return updated


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    sys.exit(main())
