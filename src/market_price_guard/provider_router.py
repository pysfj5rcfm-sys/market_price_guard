from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .freshness import now_utc
from .models import Instrument, RawPrice, Watchlist


class Provider(Protocol):
    def fetch(self, symbols: list[str]) -> dict[str, RawPrice]:
        ...


@dataclass(frozen=True)
class RouterConfig:
    provider_mode: str = "mock"


def collect_routed_prices(
    watchlist: Watchlist,
    providers: dict[str, Provider],
    config: RouterConfig,
) -> dict[str, RawPrice]:
    prices: dict[str, RawPrice] = {}
    for project in watchlist.projects.values():
        for instrument in project.instruments:
            prices[instrument.symbol] = route_symbol(instrument, providers, config)
    return prices


def route_symbol(instrument: Instrument, providers: dict[str, Provider], config: RouterConfig) -> RawPrice:
    priority = _effective_priority(instrument, config.provider_mode)
    attempts: list[dict[str, object]] = []
    last_raw: RawPrice | None = None

    for provider_name in priority:
        provider = providers.get(provider_name)
        if provider is None:
            attempts.append(_attempt(instrument.symbol, provider_name, "skipped", reason="provider_not_configured"))
            continue

        try:
            fetched = provider.fetch([instrument.symbol])
            raw = fetched.get(instrument.symbol)
        except Exception as exc:
            attempts.append(
                _attempt(
                    instrument.symbol,
                    provider_name,
                    "failed",
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                    reason="provider_exception",
                )
            )
            continue

        if raw is None:
            attempts.append(_attempt(instrument.symbol, provider_name, "failed", reason="symbol_not_found"))
            last_raw = _missing_raw(instrument, provider_name, attempts)
            continue

        provider_attempts = _provider_attempts(raw)
        attempts.extend(provider_attempts or [_raw_attempt(raw, provider_name)])
        last_raw = raw
        if _raw_usable_for_selection(raw):
            return _selected_raw(instrument, raw, provider_name, priority, attempts)

    return _final_failed_raw(instrument, last_raw, priority, attempts)


def _effective_priority(instrument: Instrument, provider_mode: str) -> list[str]:
    configured = instrument.provider_priority or [instrument.provider]
    priority = [provider for provider in configured if provider != "disabled"]
    if provider_mode == "mock":
        if "manual" in priority:
            return ["manual"]
        return ["mock"]
    return priority or [instrument.provider]


def _selected_raw(
    instrument: Instrument,
    raw: RawPrice,
    selected_provider: str,
    priority: list[str],
    attempts: list[dict[str, object]],
) -> RawPrice:
    fallback_used = bool(priority and selected_provider != priority[0])
    raw.provider_diagnostics = {
        **raw.provider_diagnostics,
        "provider_priority": priority,
        "provider_attempts": attempts,
        "selected_provider": selected_provider,
        "selected_source": raw.source,
        "selected_attempt_status": "success",
        "selected_price": raw.price if raw.price is not None else "",
        "selected_quote_time": raw.quote_time.isoformat() if raw.quote_time else "",
        "fallback_used": fallback_used,
        "fallback_reason": "primary_failed_fallback_selected" if fallback_used else "",
        "usable_for_operation": True,
        "selection_reason": "selected_provider_returned_usable_price",
    }
    if fallback_used and selected_provider == "mock" and not instrument.allow_mock_fallback_for_operation:
        raw.source = "mock_fallback"
        raw.provider_diagnostics["selected_source"] = "mock_fallback"
        raw.provider_diagnostics["usable_for_operation"] = False
        raw.provider_diagnostics["selection_reason"] = "mock_fallback_not_allowed_for_operation"
        raw.quality_issues = list(dict.fromkeys([*raw.quality_issues, "mock_fallback_not_allowed"]))
    if fallback_used and selected_provider == "manual" and not instrument.allow_manual_fallback_for_operation:
        raw.provider_diagnostics["usable_for_operation"] = False
        raw.provider_diagnostics["selection_reason"] = "manual_fallback_not_allowed_for_operation"
        raw.quality_issues = list(dict.fromkeys([*raw.quality_issues, "manual_fallback_not_allowed"]))
    return raw


def _final_failed_raw(
    instrument: Instrument,
    last_raw: RawPrice | None,
    priority: list[str],
    attempts: list[dict[str, object]],
) -> RawPrice:
    raw = last_raw or _missing_raw(instrument, priority[-1] if priority else instrument.provider, attempts)
    issues = list(raw.quality_issues)
    if not any(issue in issues for issue in ["provider_error", "symbol_not_found", "invalid_price", "quote_time_missing", "invalid_quote_time"]):
        issues.append("provider_error")
    raw.quality_issues = list(dict.fromkeys(issues))
    raw.provider_diagnostics = {
        **raw.provider_diagnostics,
        "provider_priority": priority,
        "provider_attempts": attempts,
        "selected_provider": "",
        "selected_source": raw.source,
        "selected_attempt_status": "failed",
        "selected_price": raw.price if raw.price is not None else "",
        "selected_quote_time": raw.quote_time.isoformat() if raw.quote_time else "",
        "fallback_used": False,
        "fallback_reason": "",
        "usable_for_operation": False,
        "selection_reason": "all_provider_attempts_failed",
    }
    return raw


def _raw_usable_for_selection(raw: RawPrice) -> bool:
    blocking_issues = {
        "akshare_not_installed",
        "provider_error",
        "symbol_not_found",
        "invalid_price",
        "invalid_quote_time",
        "quote_time_missing",
    }
    return raw.price is not None and raw.quote_time is not None and not (set(raw.quality_issues) & blocking_issues)


def _provider_attempts(raw: RawPrice) -> list[dict[str, object]]:
    diagnostics = raw.provider_diagnostics
    attempts = diagnostics.get("attempts")
    if not isinstance(attempts, list):
        return []
    return [
        {
            "symbol": raw.symbol,
            "provider": raw.source,
            "function_name": attempt.get("function_name", ""),
            "status": "success" if attempt.get("status") == "success" else "failed",
            "exception_type": attempt.get("exception_type", ""),
            "exception_message": attempt.get("exception_message", ""),
            "price": raw.price if attempt.get("status") == "success" else "",
            "quote_time": raw.quote_time.isoformat() if raw.quote_time and attempt.get("status") == "success" else "",
            "usable_for_operation": raw.price is not None and raw.quote_time is not None and not raw.quality_issues,
            "reason": attempt.get("exception_message", "") or ",".join(raw.quality_issues),
        }
        for attempt in attempts
        if isinstance(attempt, dict)
    ]


def _raw_attempt(raw: RawPrice, provider_name: str) -> dict[str, object]:
    status = "success" if _raw_usable_for_selection(raw) else "failed"
    return _attempt(
        raw.symbol,
        provider_name,
        status,
        function_name=str(raw.provider_diagnostics.get("function_name", provider_name)),
        price=raw.price,
        quote_time=raw.quote_time.isoformat() if raw.quote_time else "",
        usable_for_operation=status == "success",
        reason=",".join(raw.quality_issues),
    )


def _attempt(
    symbol: str,
    provider: str,
    status: str,
    function_name: str = "",
    exception_type: str = "",
    exception_message: str = "",
    price: float | None = None,
    quote_time: str = "",
    usable_for_operation: bool = False,
    reason: str = "",
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "provider": provider,
        "function_name": function_name or provider,
        "status": status,
        "exception_type": exception_type,
        "exception_message": exception_message,
        "price": "" if price is None else price,
        "quote_time": quote_time,
        "usable_for_operation": usable_for_operation,
        "reason": reason,
    }


def _missing_raw(instrument: Instrument, provider_name: str, attempts: list[dict[str, object]]) -> RawPrice:
    return RawPrice(
        symbol=instrument.symbol,
        price=None,
        currency="",
        source=provider_name,
        name=instrument.name,
        market=instrument.market,
        quote_time=None,
        fetch_time=now_utc(),
        market_status="unknown",
        quality_issues=["symbol_not_found"],
        provider_diagnostics={"provider_attempts": attempts},
    )
