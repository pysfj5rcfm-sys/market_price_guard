from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from market_price_guard.freshness import now_utc
from market_price_guard.models import RawPrice
from market_price_guard.providers.base import PriceProvider


class ManualProvider(PriceProvider):
    def __init__(self, config_path: Path):
        self.config_path = config_path

    def fetch(self, symbols: list[str]) -> dict[str, RawPrice]:
        data = self._load()
        wanted = set(symbols)
        prices = {}
        fetch_time = now_utc()
        for item in data.get("manual_prices", []):
            symbol = str(item.get("symbol", ""))
            if symbol not in wanted:
                continue
            prices[symbol] = self._to_raw_price(item, fetch_time)
        return prices

    def _load(self) -> dict:
        with self.config_path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}

    def _to_raw_price(self, item: dict[str, Any], fetch_time: datetime) -> RawPrice:
        quality_issues: list[str] = []
        price = _parse_positive_price(item.get("price"))
        if price is None:
            quality_issues.append("invalid_price")

        quote_time = _parse_datetime(item.get("quote_time"))
        if item.get("quote_time") in (None, ""):
            quality_issues.append("quote_time_missing")
        elif quote_time is None:
            quality_issues.append("invalid_quote_time")

        return RawPrice(
            symbol=str(item.get("symbol", "")),
            name=item.get("name"),
            market=item.get("market"),
            price=price,
            currency=str(item.get("currency", "")),
            source="manual",
            quote_time=quote_time,
            fetch_time=fetch_time,
            entry_time=quote_time,
            market_status="manual",
            source_note=item.get("source_note"),
            product_type=item.get("product_type"),
            price_type=item.get("price_type"),
            tradable=item.get("tradable"),
            fee_note=item.get("fee_note"),
            project=item.get("project"),
            asset_role=item.get("asset_role"),
            required_for_operation=item.get("required_for_operation"),
            quality_issues=quality_issues,
        )


def _parse_positive_price(value: Any) -> float | None:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None
    return price


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
