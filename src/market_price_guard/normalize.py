from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .freshness import assess_freshness, now_utc
from .models import PriceRecord, RawPrice, Watchlist


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def load_watchlist(path: Path) -> Watchlist:
    return Watchlist.model_validate(load_yaml(path))


def normalize_records(
    watchlist: Watchlist,
    raw_prices: dict[str, RawPrice],
    rules: dict[str, Any],
    now: datetime | None = None,
) -> list[PriceRecord]:
    records: list[PriceRecord] = []
    current_time = now or now_utc()

    for project_key, project in watchlist.projects.items():
        for instrument in project.instruments:
            raw = raw_prices.get(instrument.symbol)
            if raw is None:
                raw = RawPrice(
                    symbol=instrument.symbol,
                    price=None,
                    currency="",
                    source=instrument.provider,
                    quote_time=None,
                    fetch_time=current_time,
                    market_status="unknown",
                    quality_issues=["missing_price"],
                )

            is_stale, stale_reason = assess_freshness(raw, instrument.market, rules, now=current_time)
            records.append(
                PriceRecord(
                    project=project_key,
                    symbol=instrument.symbol,
                    name=raw.name or instrument.name,
                    market=instrument.market,
                    price=raw.price,
                    currency=raw.currency,
                    source=raw.source,
                    quote_time=raw.quote_time,
                    fetch_time=raw.fetch_time or current_time,
                    market_status=raw.market_status,
                    is_stale=is_stale,
                    stale_reason=stale_reason,
                    core=instrument.core,
                    required_for_operation=raw.required_for_operation
                    if raw.required_for_operation is not None
                    else instrument.required_for_operation,
                    source_note=raw.source_note,
                    product_type=raw.product_type,
                    price_type=raw.price_type,
                    tradable=raw.tradable,
                    fee_note=raw.fee_note,
                    asset_role=raw.asset_role or instrument.asset_role,
                    quality_issues=raw.quality_issues,
                )
            )
    return records
