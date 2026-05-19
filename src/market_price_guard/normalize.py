from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .freshness import assess_freshness, market_status_for_now, now_utc
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

            effective_market_status = market_status_for_now(raw, instrument.market, current_time)
            is_stale, stale_reason = assess_freshness(raw, instrument.market, rules, now=current_time)
            provider_diagnostics = dict(raw.provider_diagnostics)
            provider_diagnostics.update(_freshness_diagnostics(raw, instrument.market, rules, current_time, effective_market_status))
            required_for_operation = (
                raw.required_for_operation
                if raw.required_for_operation is not None
                else instrument.required_for_operation
            )
            trust = _quote_trust_fields(raw, is_stale, required_for_operation)
            provider_diagnostics.update(
                {
                    "quote_trust_tier": trust["quote_trust_tier"],
                    "usable_for_reference": trust["usable_for_reference"],
                    "quote_purpose": trust["quote_purpose"],
                    "confirmation_required": trust["confirmation_required"],
                    "operation_blocking_reason": trust["operation_blocking_reason"],
                    "reference_note": trust["reference_note"],
                }
            )
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
                    market_status=effective_market_status,
                    is_stale=is_stale,
                    stale_reason=stale_reason,
                    core=instrument.core,
                    required_for_operation=required_for_operation,
                    source_note=raw.source_note,
                    product_type=raw.product_type,
                    price_type=raw.price_type,
                    tradable=raw.tradable,
                    fee_note=raw.fee_note,
                    asset_role=raw.asset_role or instrument.asset_role,
                    quality_issues=raw.quality_issues,
                    provider_diagnostics=provider_diagnostics,
                    selected_provider=str(provider_diagnostics.get("selected_provider") or raw.source),
                    usable_for_operation=bool(trust["usable_for_operation"]),
                    quote_trust_tier=str(trust["quote_trust_tier"]),
                    usable_for_reference=bool(trust["usable_for_reference"]),
                    quote_purpose=str(trust["quote_purpose"]),
                    confirmation_required=bool(trust["confirmation_required"]),
                    operation_blocking_reason=str(trust["operation_blocking_reason"]),
                    reference_note=str(trust["reference_note"]),
                )
            )
    return records


def _quote_trust_fields(raw: RawPrice, is_stale: bool, required_for_operation: bool) -> dict[str, object]:
    issues = set(raw.quality_issues)
    invalid = bool(
        raw.price is None
        or raw.quote_time is None
        or issues
        & {
            "provider_error",
            "akshare_not_installed",
            "yfinance_not_installed",
            "symbol_not_found",
            "invalid_price",
            "invalid_quote_time",
            "quote_time_missing",
            "provider_timeout",
            "mock_fallback_not_allowed",
            "manual_fallback_not_allowed",
        }
    )
    operation_blocking_reason = _operation_blocking_reason(raw, is_stale)
    usable_for_operation = not invalid and not is_stale
    usable_for_reference = raw.price is not None and raw.quote_time is not None and not (
        issues
        & {
            "provider_error",
            "akshare_not_installed",
            "yfinance_not_installed",
            "symbol_not_found",
            "invalid_price",
            "invalid_quote_time",
            "quote_time_missing",
            "provider_timeout",
        }
    )
    if invalid:
        return {
            "quote_trust_tier": raw.quote_trust_tier or "development",
            "usable_for_reference": False,
            "usable_for_operation": False,
            "quote_purpose": raw.quote_purpose,
            "confirmation_required": True,
            "operation_blocking_reason": operation_blocking_reason,
            "reference_note": raw.reference_note,
        }
    if raw.source in {"mock", "mock_fallback"}:
        return {
            "quote_trust_tier": raw.quote_trust_tier or "development",
            "usable_for_reference": False,
            "usable_for_operation": False,
            "quote_purpose": raw.quote_purpose,
            "confirmation_required": True,
            "operation_blocking_reason": operation_blocking_reason or "development_price_not_operation_grade",
            "reference_note": raw.reference_note or "mock data is for development/testing only",
        }
    if raw.source == "yfinance":
        yfinance_etf_symbols = {"159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"}
        yfinance_operation_usable = usable_for_operation and raw.symbol not in yfinance_etf_symbols
        yfinance_blocking_reason = operation_blocking_reason
        if raw.symbol in yfinance_etf_symbols and not yfinance_blocking_reason:
            yfinance_blocking_reason = "reference_tier_requires_operation_confirmation"
        return {
            "quote_trust_tier": raw.quote_trust_tier or "reference",
            "usable_for_reference": usable_for_reference,
            "usable_for_operation": yfinance_operation_usable,
            "quote_purpose": raw.quote_purpose,
            "confirmation_required": True,
            "operation_blocking_reason": yfinance_blocking_reason,
            "reference_note": raw.reference_note
            or "yfinance is an open-source Yahoo Finance public API wrapper; not an official exchange feed",
        }
    return {
        "quote_trust_tier": raw.quote_trust_tier or "operation",
        "usable_for_reference": usable_for_reference,
        "usable_for_operation": usable_for_operation,
        "quote_purpose": raw.quote_purpose,
        "confirmation_required": bool(raw.confirmation_required) if raw.confirmation_required is not None else False,
        "operation_blocking_reason": operation_blocking_reason,
        "reference_note": raw.reference_note,
    }


def _operation_blocking_reason(raw: RawPrice, is_stale: bool) -> str:
    issues = set(raw.quality_issues)
    for issue in [
        "provider_error",
        "provider_timeout",
        "symbol_not_found",
        "invalid_price",
        "invalid_quote_time",
        "quote_time_missing",
        "mock_fallback_not_allowed",
        "manual_fallback_not_allowed",
    ]:
        if issue in issues:
            return issue
    if raw.price is None:
        return "missing_price"
    if raw.quote_time is None:
        return "quote_time_missing"
    if is_stale:
        return "stale"
    return ""


def _freshness_diagnostics(raw: RawPrice, market: str, rules: dict[str, Any], current_time: datetime, market_status: str) -> dict[str, object]:
    diagnostics: dict[str, object] = {
        "fetch_time_utc": _to_utc(raw.fetch_time or current_time).isoformat(),
    }
    max_age = _max_age_seconds(raw, market, rules, market_status)
    if max_age is not None:
        diagnostics["max_age_seconds"] = max_age
    if raw.quote_time is not None:
        quote_utc = _to_utc(raw.quote_time)
        diagnostics["quote_time_utc"] = quote_utc.isoformat()
        diagnostics["age_seconds"] = max(0, int((_to_utc(current_time) - quote_utc).total_seconds()))
    return diagnostics


def _max_age_seconds(raw: RawPrice, market: str, rules: dict[str, Any], market_status: str) -> int | None:
    if raw.source == "manual" or market == "MANUAL":
        return int(rules.get("MANUAL", rules.get("manual", {})).get("max_age_seconds", 0))
    market_rules = rules.get("markets", {}).get(market, rules.get("default", {}))
    if market_status == "closed":
        return int(market_rules.get("max_age_seconds_closed", rules.get("default", {}).get("max_age_seconds_closed", 0)))
    return int(market_rules.get("max_age_seconds_open", rules.get("default", {}).get("max_age_seconds_open", 0)))


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
