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
            base_quote = _base_quote_fields(raw, instrument.market)
            provider_diagnostics.update(
                {
                    "base_quote_completeness": base_quote["base_quote_completeness"],
                    "base_quote_missing_fields": base_quote["base_quote_missing_fields"],
                    "base_quote_fields_available_count": base_quote["base_quote_fields_available_count"],
                    "base_quote_fields_missing_count": base_quote["base_quote_fields_missing_count"],
                    "exchange": base_quote["exchange"],
                    "country_market": base_quote["country_market"],
                    "trading_calendar": base_quote["trading_calendar"],
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
                    asset_type=instrument.asset_type or "",
                    project_scope=instrument.project_scope or project_key,
                    role=instrument.role or instrument.asset_role or "",
                    universe_tags=instrument.universe_tags,
                    universe_type=instrument.universe_type,
                    default_quote_purpose=instrument.default_quote_purpose or "",
                    report_group=instrument.report_group or "",
                    notes=instrument.notes or "",
                    registry_found=instrument.registry_found,
                    unsupported_reason=instrument.unsupported_reason,
                    **base_quote,
                )
            )
    return records


def _base_quote_fields(raw: RawPrice, market: str) -> dict[str, object]:
    provider_source = str(raw.provider_diagnostics.get("selected_provider") or raw.source or "")
    last_price = raw.last_price if raw.last_price is not None else raw.price
    values: dict[str, float | None] = {
        "last_price": last_price,
        "prev_close": raw.prev_close,
        "open_price": raw.open_price,
        "high_price": raw.high_price,
        "low_price": raw.low_price,
        "volume": raw.volume,
        "amount": raw.amount,
        "price_change": raw.price_change,
        "price_change_pct": raw.price_change_pct,
        "amplitude_pct": raw.amplitude_pct,
    }
    sources = {
        "last_price_source": raw.last_price_source or (provider_source if last_price is not None else "missing"),
        "prev_close_source": raw.prev_close_source or (provider_source if raw.prev_close is not None else "missing"),
        "open_price_source": raw.open_price_source or (provider_source if raw.open_price is not None else "missing"),
        "high_price_source": raw.high_price_source or (provider_source if raw.high_price is not None else "missing"),
        "low_price_source": raw.low_price_source or (provider_source if raw.low_price is not None else "missing"),
        "volume_source": raw.volume_source or (provider_source if raw.volume is not None else "missing"),
        "amount_source": raw.amount_source or (provider_source if raw.amount is not None else "missing"),
        "price_change_source": raw.price_change_source or (provider_source if raw.price_change is not None else "missing"),
        "price_change_pct_source": raw.price_change_pct_source or (provider_source if raw.price_change_pct is not None else "missing"),
        "amplitude_pct_source": raw.amplitude_pct_source or (provider_source if raw.amplitude_pct is not None else "missing"),
    }
    errors: list[str] = []
    prev_close = values["prev_close"]
    if values["price_change"] is None and last_price is not None and prev_close is not None:
        values["price_change"] = round(last_price - prev_close, 6)
        sources["price_change_source"] = "calculated_from_last_and_prev_close"
    if values["price_change_pct"] is None and last_price is not None and prev_close is not None:
        if prev_close > 0:
            values["price_change_pct"] = round((last_price - prev_close) / prev_close * 100, 6)
            sources["price_change_pct_source"] = "calculated_from_last_and_prev_close"
        else:
            errors.append("price_change_pct_prev_close_not_positive")
    high_price = values["high_price"]
    low_price = values["low_price"]
    if values["amplitude_pct"] is None and high_price is not None and low_price is not None and prev_close is not None:
        if prev_close > 0:
            values["amplitude_pct"] = round((high_price - low_price) / prev_close * 100, 6)
            sources["amplitude_pct_source"] = "calculated_from_high_low_prev_close"
        else:
            errors.append("amplitude_pct_prev_close_not_positive")

    required_fields = ["last_price", "prev_close", "open_price", "high_price", "low_price", "volume", "amount"]
    missing_fields = [field for field in required_fields if values[field] is None]
    available_count = len(required_fields) - len(missing_fields)
    optional_available = available_count - (1 if values["last_price"] is not None else 0)
    if values["last_price"] is None:
        completeness = "missing"
    elif not missing_fields:
        completeness = "complete"
    elif optional_available >= 3:
        completeness = "partial"
    else:
        completeness = "price_only"

    exchange_fields = _exchange_fields(raw.symbol, market)
    return {
        **values,
        **sources,
        "base_quote_missing_fields": ",".join(missing_fields),
        "base_quote_field_errors": ",".join(errors),
        "base_quote_completeness": completeness,
        "base_quote_fields_available_count": available_count,
        "base_quote_fields_missing_count": len(missing_fields),
        **exchange_fields,
    }


def _exchange_fields(symbol: str, market: str) -> dict[str, str]:
    if symbol.endswith(".SZ"):
        return {"exchange": "SZ", "country_market": "CN", "trading_calendar": "CN_A_SHARE"}
    if symbol.endswith(".SH"):
        return {"exchange": "SH", "country_market": "CN", "trading_calendar": "CN_A_SHARE"}
    if symbol.endswith(".HK"):
        return {"exchange": "HK", "country_market": "HK", "trading_calendar": "HK"}
    if symbol in {"GOLD_CNY"} or market == "MANUAL":
        return {"exchange": "MANUAL", "country_market": "MANUAL", "trading_calendar": "MANUAL"}
    if symbol in {"USD_CNY", "HKD_CNY"} or market == "FX":
        return {"exchange": "FX", "country_market": "FX", "trading_calendar": "FX"}
    if symbol == "IXIC" or market in {"US", "INDEX"}:
        return {"exchange": "US", "country_market": "US", "trading_calendar": "US"}
    return {"exchange": market or "UNKNOWN", "country_market": market or "UNKNOWN", "trading_calendar": market or "UNKNOWN"}


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
    if raw.source == "eastmoney_direct":
        return {
            "quote_trust_tier": raw.quote_trust_tier or "reference",
            "usable_for_reference": usable_for_reference,
            "usable_for_operation": False,
            "quote_purpose": raw.quote_purpose,
            "confirmation_required": True,
            "operation_blocking_reason": operation_blocking_reason or "reference_tier_requires_operation_confirmation",
            "reference_note": raw.reference_note
            or "Eastmoney Direct uses Eastmoney public web quote endpoint; not an official exchange real-time feed; first version is reference-grade / operation-candidate only",
        }
    if raw.source == "yfinance":
        yfinance_etf_symbols = {"159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"}
        yfinance_operation_usable = usable_for_operation and raw.symbol not in yfinance_etf_symbols
        yfinance_blocking_reason = operation_blocking_reason
        if raw.symbol in yfinance_etf_symbols and not yfinance_blocking_reason:
            yfinance_blocking_reason = "reference_tier_requires_operation_confirmation"
        yfinance_confirmation_required = raw.symbol in yfinance_etf_symbols or raw.quote_purpose == "reference"
        return {
            "quote_trust_tier": raw.quote_trust_tier or "reference",
            "usable_for_reference": usable_for_reference,
            "usable_for_operation": yfinance_operation_usable,
            "quote_purpose": raw.quote_purpose,
            "confirmation_required": yfinance_confirmation_required,
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
