from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .normalize import load_watchlist, load_yaml, normalize_records
from .provider_router import RouterConfig, collect_routed_prices
from .models import WatchProject, Watchlist
from .providers.akshare_provider import AkshareProvider
from .providers.eastmoney_direct_provider import EastmoneyDirectProvider
from .providers.manual_provider import ManualProvider
from .providers.mock_provider import MockProvider
from .providers.yfinance_provider import YFinanceProvider
from .report import CompletenessSummary, build_completeness_summary, format_blocking_record, write_outputs


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
MANUAL_PRICES_PATH = CONFIG_DIR / "manual_prices.yaml"

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
) -> dict:
    watchlist = _filter_watchlist(load_watchlist(watchlist_path), profile)
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
        ),
    )
    return {"watchlist": watchlist, "prices": prices}


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
    max_run_seconds: float = 30.0,
    max_data_lag_seconds: float = 300.0,
) -> PipelineResult:
    perf_start = time.perf_counter()
    run_start = _utc_now_iso()
    collected = collect_prices(
        watchlist_path,
        mock_prices_path,
        manual_prices_path,
        provider_mode,
        profile,
        timeout_seconds,
        provider_policy,
        quote_purpose,
    )
    rules = load_yaml(stale_rules_path)
    records = normalize_records(collected["watchlist"], collected["prices"], rules)
    elapsed = time.perf_counter() - perf_start
    runtime = _runtime_diagnostics(
        records=records,
        run_start_time_utc=run_start,
        total_elapsed_seconds=elapsed,
        profile=profile,
        provider_mode=provider_mode,
        provider_policy=provider_policy,
        quote_purpose=quote_purpose,
        strict=strict,
        max_run_seconds=max_run_seconds,
        max_data_lag_seconds=max_data_lag_seconds,
    )
    completeness = build_completeness_summary(records)
    exit_code = EXIT_STRICT_BLOCKED if strict and not completeness.usable_for_operation else EXIT_OK
    runtime["exit_code"] = exit_code
    write_outputs(records, output_dir, provider_mode=provider_mode, runtime=runtime)
    return PipelineResult(
        records_count=len(records),
        output_dir=output_dir,
        strict=strict,
        completeness=completeness,
        exit_code=exit_code,
        runtime=runtime,
    )


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
            strict=args.strict,
            profile=args.profile,
            timeout_seconds=args.timeout_seconds,
            max_run_seconds=args.max_run_seconds,
            max_data_lag_seconds=args.max_data_lag_seconds,
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
    strict: bool,
    max_run_seconds: float,
    max_data_lag_seconds: float,
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
        "max_run_seconds": max_run_seconds,
        "max_data_lag_seconds": max_data_lag_seconds,
        "run_time_budget_exceeded": total_elapsed_seconds > max_run_seconds,
        "max_quote_lag_seconds": "" if max_quote_lag is None else round(max_quote_lag, 3),
    }


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    sys.exit(main())
