from __future__ import annotations

from market_price_guard.models import RawPrice
from market_price_guard.providers.base import PriceProvider


class AkshareProvider(PriceProvider):
    def fetch(self, symbols: list[str]) -> dict[str, RawPrice]:
        raise NotImplementedError("akshare provider is not implemented in version 1")
