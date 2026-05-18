from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from .normalize import load_watchlist, load_yaml, normalize_records
from .providers.manual_provider import ManualProvider
from .providers.mock_provider import MockProvider
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate price freshness reports from mock/manual data.")
    parser.add_argument("--watchlist", type=Path, default=CONFIG_DIR / "watchlist.yaml")
    parser.add_argument("--stale-rules", type=Path, default=CONFIG_DIR / "stale_rules.yaml")
    parser.add_argument("--mock-prices", type=Path, default=CONFIG_DIR / "mock_prices.yaml")
    parser.add_argument("--manual-prices", type=Path, default=MANUAL_PRICES_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--strict", action="store_true", help="Return exit code 2 when required price data is unusable.")
    return parser.parse_args(argv)


def collect_prices(watchlist_path: Path, mock_prices_path: Path, manual_prices_path: Path) -> dict:
    watchlist = load_watchlist(watchlist_path)
    mock_provider = MockProvider(mock_prices_path)
    manual_provider = ManualProvider(manual_prices_path)

    mock_symbols: list[str] = []
    manual_symbols: list[str] = []
    for project in watchlist.projects.values():
        for instrument in project.instruments:
            if instrument.provider == "manual":
                manual_symbols.append(instrument.symbol)
            else:
                mock_symbols.append(instrument.symbol)

    prices = {}
    prices.update(mock_provider.fetch(mock_symbols))
    # Manual records intentionally override mock values for the same symbol.
    prices.update(manual_provider.fetch(manual_symbols))
    return {"watchlist": watchlist, "prices": prices}


def run_pipeline(
    watchlist_path: Path = CONFIG_DIR / "watchlist.yaml",
    stale_rules_path: Path = CONFIG_DIR / "stale_rules.yaml",
    mock_prices_path: Path = CONFIG_DIR / "mock_prices.yaml",
    manual_prices_path: Path = MANUAL_PRICES_PATH,
    output_dir: Path = OUTPUT_DIR,
    strict: bool = False,
) -> PipelineResult:
    collected = collect_prices(watchlist_path, mock_prices_path, manual_prices_path)
    rules = load_yaml(stale_rules_path)
    records = normalize_records(collected["watchlist"], collected["prices"], rules)
    write_outputs(records, output_dir)
    completeness = build_completeness_summary(records)
    exit_code = EXIT_STRICT_BLOCKED if strict and not completeness.usable_for_operation else EXIT_OK
    return PipelineResult(
        records_count=len(records),
        output_dir=output_dir,
        strict=strict,
        completeness=completeness,
        exit_code=exit_code,
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
            strict=args.strict,
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
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
