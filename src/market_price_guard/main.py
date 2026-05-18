from __future__ import annotations

from pathlib import Path

from .normalize import load_watchlist, load_yaml, normalize_records
from .providers.manual_provider import ManualProvider
from .providers.mock_provider import MockProvider
from .report import write_outputs


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
OUTPUT_DIR = PROJECT_ROOT / "outputs"


def collect_prices() -> dict:
    watchlist = load_watchlist(CONFIG_DIR / "watchlist.yaml")
    mock_provider = MockProvider(CONFIG_DIR / "mock_prices.yaml")
    manual_provider = ManualProvider(CONFIG_DIR / "mock_prices.yaml")

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
    prices.update(manual_provider.fetch(manual_symbols))
    return {"watchlist": watchlist, "prices": prices}


def main() -> None:
    collected = collect_prices()
    rules = load_yaml(CONFIG_DIR / "stale_rules.yaml")
    records = normalize_records(collected["watchlist"], collected["prices"], rules)
    write_outputs(records, OUTPUT_DIR)
    print(f"Generated {len(records)} price records in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
