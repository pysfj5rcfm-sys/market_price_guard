from __future__ import annotations

from datetime import datetime, timezone
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
            provider_diagnostics = dict(raw.provider_diagnostics)
            provider_diagnostics.update(_freshness_diagnostics(raw, instrument.market, rules, current_time))
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
                    provider_diagnostics=provider_diagnostics,
                )
            )
    return records


def _freshness_diagnostics(raw: RawPrice, market: str, rules: dict[str, Any], current_time: datetime) -> dict[str, object]:
    diagnostics: dict[str, object] = {
        "fetch_time_utc": _to_utc(raw.fetch_time or current_time).isoformat(),
    }
    max_age = _max_age_seconds(raw, market, rules)
    if max_age is not None:
        diagnostics["max_age_seconds"] = max_age
    if raw.quote_time is not None:
        quote_utc = _to_utc(raw.quote_time)
        diagnostics["quote_time_utc"] = quote_utc.isoformat()
        diagnostics["age_seconds"] = max(0, int((_to_utc(current_time) - quote_utc).total_seconds()))
    return diagnostics


def _max_age_seconds(raw: RawPrice, market: str, rules: dict[str, Any]) -> int | None:
    if raw.source == "manual" or market == "MANUAL":
        return int(rules.get("MANUAL", rules.get("manual", {})).get("max_age_seconds", 0))
    market_rules = rules.get("markets", {}).get(market, rules.get("default", {}))
    if raw.market_status == "closed":
        return int(market_rules.get("max_age_seconds_closed", rules.get("default", {}).get("max_age_seconds_closed", 0)))
    return int(market_rules.get("max_age_seconds_open", rules.get("default", {}).get("max_age_seconds_open", 0)))


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
