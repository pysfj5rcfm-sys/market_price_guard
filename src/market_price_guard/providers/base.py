from __future__ import annotations

from abc import ABC, abstractmethod

from market_price_guard.models import RawPrice


class PriceProvider(ABC):
    @abstractmethod
    def fetch(self, symbols: list[str]) -> dict[str, RawPrice]:
        """Fetch prices keyed by symbol."""
