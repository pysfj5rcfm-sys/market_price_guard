from __future__ import annotations

from pathlib import Path

import yaml

from market_price_guard.models import RawPrice
from market_price_guard.providers.base import PriceProvider


class MockProvider(PriceProvider):
    def __init__(self, config_path: Path):
        self.config_path = config_path

    def fetch(self, symbols: list[str]) -> dict[str, RawPrice]:
        data = self._load()
        wanted = set(symbols)
        prices = {}
        for item in data.get("prices", []):
            raw = RawPrice.model_validate(item)
            if raw.symbol in wanted:
                prices[raw.symbol] = raw
        return prices

    def _load(self) -> dict:
        with self.config_path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
