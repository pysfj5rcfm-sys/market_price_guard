from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from .freshness import now_utc
from .models import Instrument, RawPrice, Watchlist


ETF_SYMBOLS = {"159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"}
ENERGY_A_SHARE_SYMBOLS = {"601899.SH", "601985.SH", "003816.SZ"}
HK_SYMBOLS = {"00883.HK"}
EASTMONEY_DIRECT_SYMBOLS = ETF_SYMBOLS | ENERGY_A_SHARE_SYMBOLS


class Provider(Protocol):
    def fetch(self, symbols: list[str]) -> dict[str, RawPrice]:
        ...


@dataclass(frozen=True)
class RouterConfig:
    provider_mode: str = "mock"
    provider_policy: str = "fast"
    timeout_seconds: float = 8.0
    quote_purpose: str = "operation"
    reconcile_mode: str = "default"


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
    configured_priority = [provider for provider in (instrument.provider_priority or [instrument.provider]) if provider != "disabled"]
    priority = _effective_priority(instrument, config.provider_mode, config.provider_policy, config.quote_purpose)
    attempts: list[dict[str, object]] = []
    last_raw: RawPrice | None = None

    for provider_name in priority:
        provider = providers.get(provider_name)
        if provider is None:
            attempts.append(_attempt(instrument.symbol, provider_name, "skipped", reason="provider_not_configured", elapsed_seconds=0.0))
            continue

        start = time.perf_counter()
        try:
            fetched = provider.fetch([instrument.symbol])
            raw = fetched.get(instrument.symbol)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            attempts.append(
                _attempt(
                    instrument.symbol,
                    provider_name,
                    "failed",
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                    reason="provider_timeout" if elapsed > config.timeout_seconds else "provider_exception",
                    elapsed_seconds=elapsed,
                    timeout_seconds=config.timeout_seconds,
                )
            )
            continue
        elapsed = time.perf_counter() - start

        if raw is None:
            attempts.append(
                _attempt(
                    instrument.symbol,
                    provider_name,
                    "failed",
                    reason="provider_timeout" if elapsed > config.timeout_seconds else "symbol_not_found",
                    elapsed_seconds=elapsed,
                    timeout_seconds=config.timeout_seconds,
                )
            )
            last_raw = _missing_raw(instrument, provider_name, attempts)
            continue

        provider_attempts = _provider_attempts(raw)
        stamped_attempts = _stamp_elapsed(provider_attempts or [_raw_attempt(raw, provider_name)], elapsed, config.timeout_seconds)
        if elapsed > config.timeout_seconds and not _raw_usable_for_selection(raw):
            raw.quality_issues = list(dict.fromkeys([*raw.quality_issues, "provider_timeout", "provider_error"]))
            stamped_attempts = [
                {**attempt, "status": "failed", "reason": "provider_timeout"}
                for attempt in stamped_attempts
            ]
        attempts.extend(stamped_attempts)
        last_raw = raw
        if _raw_usable_for_selection(raw):
            _attach_reconciliation_candidates(instrument, providers, config, raw, provider_name, priority, attempts)
            return _selected_raw(instrument, raw, provider_name, priority, configured_priority, config.provider_policy, config.quote_purpose, attempts)

    return _final_failed_raw(instrument, last_raw, priority, configured_priority, config.provider_policy, config.quote_purpose, attempts)


def _effective_priority(instrument: Instrument, provider_mode: str, provider_policy: str, quote_purpose: str = "operation") -> list[str]:
    configured = instrument.provider_priority or [instrument.provider]
    priority = [provider for provider in configured if provider != "disabled"]
    if provider_mode == "mock":
        if "manual" in priority:
            return ["manual"]
        return ["mock"]
    if provider_policy == "fast":
        return _policy_priority(instrument, ["yfinance", "akshare", "mock"], quote_purpose=quote_purpose)
    if provider_policy == "conservative":
        return _policy_priority(instrument, ["akshare", "yfinance", "mock"], quote_purpose=quote_purpose)
    if provider_policy == "diagnostic":
        return _diagnostic_priority(instrument, priority, quote_purpose)
    return priority or [instrument.provider]


def _selected_raw(
    instrument: Instrument,
    raw: RawPrice,
    selected_provider: str,
    priority: list[str],
    configured_priority: list[str],
    provider_policy: str,
    quote_purpose: str,
    attempts: list[dict[str, object]],
) -> RawPrice:
    fallback_used = bool(priority and selected_provider != priority[0])
    attempted_after_selection = {
        str(attempt.get("provider", ""))
        for attempt in attempts
        if attempt.get("provider") != selected_provider and attempt.get("status") != "skipped"
    }
    skipped = [
        attempt
        for attempt in _skipped_after_success(raw.symbol, priority, selected_provider, provider_policy, quote_purpose)
        if attempt.get("provider") not in attempted_after_selection
    ]
    attempts = [*attempts, *skipped]
    raw.quote_purpose = quote_purpose
    raw.provider_diagnostics = {
        **raw.provider_diagnostics,
        "configured_provider_priority": configured_priority,
        "provider_priority": priority,
        "effective_provider_chain": priority,
        "provider_policy": provider_policy,
        "quote_purpose": quote_purpose,
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
    if selected_provider == "eastmoney_direct":
        raw.provider_diagnostics["usable_for_operation"] = False
        raw.provider_diagnostics["selection_reason"] = "eastmoney_direct_reference_candidate_selected"
        raw.operation_blocking_reason = raw.operation_blocking_reason or "reference_tier_requires_operation_confirmation"
        raw.confirmation_required = True
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
    configured_priority: list[str],
    provider_policy: str,
    quote_purpose: str,
    attempts: list[dict[str, object]],
) -> RawPrice:
    raw = last_raw or _missing_raw(instrument, priority[-1] if priority else instrument.provider, attempts)
    raw.quote_purpose = quote_purpose
    issues = list(raw.quality_issues)
    if not any(issue in issues for issue in ["provider_error", "symbol_not_found", "invalid_price", "quote_time_missing", "invalid_quote_time"]):
        issues.append("provider_error")
    raw.quality_issues = list(dict.fromkeys(issues))
    raw.provider_diagnostics = {
        **raw.provider_diagnostics,
        "configured_provider_priority": configured_priority,
        "provider_priority": priority,
        "effective_provider_chain": priority,
        "provider_policy": provider_policy,
        "quote_purpose": quote_purpose,
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
        "provider_timeout",
    }
    return raw.price is not None and raw.quote_time is not None and not (set(raw.quality_issues) & blocking_issues)


def _attach_reconciliation_candidates(
    instrument: Instrument,
    providers: dict[str, Provider],
    config: RouterConfig,
    selected_raw: RawPrice,
    selected_provider: str,
    priority: list[str],
    attempts: list[dict[str, object]],
) -> None:
    if config.provider_mode != "live" or instrument.symbol not in EASTMONEY_DIRECT_SYMBOLS:
        return
    candidate_providers = _reconciliation_candidate_providers(instrument, config, selected_provider, priority)
    existing_sources = _reconciliation_sources_from_attempts(attempts, selected_provider)
    if not candidate_providers and not existing_sources:
        return
    sources: list[dict[str, object]] = list(existing_sources)
    already_attempted = {str(source.get("source", "")) for source in sources}
    for provider_name in candidate_providers:
        if provider_name in already_attempted:
            continue
        provider = providers.get(provider_name)
        if provider is None:
            continue
        start = time.perf_counter()
        try:
            fetched = provider.fetch([instrument.symbol])
            candidate = fetched.get(instrument.symbol)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            attempts.append(
                _attempt(
                    instrument.symbol,
                    provider_name,
                    "failed",
                    function_name=f"{provider_name}.reconciliation",
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                    reason="reconciliation_provider_exception",
                    elapsed_seconds=elapsed,
                    timeout_seconds=config.timeout_seconds,
                )
            )
            sources.append(
                {
                    "source": provider_name,
                    "status": "provider_error",
                    "quality_issues": ["provider_error"],
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                }
            )
            continue
        elapsed = time.perf_counter() - start
        if candidate is None:
            attempts.append(
                _attempt(
                    instrument.symbol,
                    provider_name,
                    "failed",
                    function_name=f"{provider_name}.reconciliation",
                    reason="reconciliation_symbol_not_found",
                    elapsed_seconds=elapsed,
                    timeout_seconds=config.timeout_seconds,
                )
            )
            sources.append({"source": provider_name, "status": "symbol_not_found", "quality_issues": ["symbol_not_found"]})
            continue
        attempts.extend(_stamp_elapsed(_provider_attempts(candidate) or [_raw_attempt(candidate, provider_name)], elapsed, config.timeout_seconds))
        sources.append(
            {
                "source": candidate.source,
                "provider": provider_name,
                "status": "success" if _raw_usable_for_selection(candidate) else "failed",
                "price": candidate.price if candidate.price is not None else "",
                "quote_time": candidate.quote_time.isoformat() if candidate.quote_time else "",
                "quality_issues": candidate.quality_issues,
                "quote_trust_tier": candidate.quote_trust_tier or "",
            }
        )
    if sources:
        selected_raw.provider_diagnostics = {
            **selected_raw.provider_diagnostics,
            "reconciliation_enabled": True,
            "reconciliation_sources": sources,
        }


def _reconciliation_candidate_providers(instrument: Instrument, config: RouterConfig, selected_provider: str, priority: list[str]) -> list[str]:
    if config.reconcile_mode == "full" and instrument.symbol in ETF_SYMBOLS:
        ordered = ["eastmoney_direct", "yfinance", "akshare"]
    elif config.provider_policy == "diagnostic":
        ordered = ["eastmoney_direct", "akshare", "yfinance"]
    elif config.quote_purpose == "reference" and selected_provider == "eastmoney_direct":
        ordered = ["yfinance"]
    else:
        return []
    if instrument.symbol in ETF_SYMBOLS:
        candidates = ordered
    elif instrument.symbol in ENERGY_A_SHARE_SYMBOLS:
        candidates = [provider for provider in ordered if provider in {"eastmoney_direct", "yfinance"}]
    else:
        candidates = []
    return [provider for provider in candidates if provider != selected_provider and provider in priority + ["yfinance", "akshare", "eastmoney_direct"]]


def _reconciliation_sources_from_attempts(attempts: list[dict[str, object]], selected_provider: str) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    seen: set[str] = set()
    for attempt in attempts:
        provider = str(attempt.get("provider", ""))
        if provider in seen or provider == selected_provider or provider not in {"eastmoney_direct", "akshare", "yfinance"}:
            continue
        if attempt.get("status") == "success":
            continue
        seen.add(provider)
        sources.append(
            {
                "source": provider,
                "status": "provider_error" if attempt.get("exception_type") else str(attempt.get("reason") or "failed"),
                "quality_issues": ["provider_error"] if attempt.get("exception_type") else ["symbol_not_found"],
                "exception_type": attempt.get("exception_type", ""),
                "exception_message": attempt.get("exception_message", ""),
            }
        )
    return sources


def _provider_attempts(raw: RawPrice) -> list[dict[str, object]]:
    diagnostics = raw.provider_diagnostics
    attempts = diagnostics.get("attempts")
    if not isinstance(attempts, list):
        return []
    usable = False if raw.source == "eastmoney_direct" else _raw_usable_for_selection(raw)
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
            "usable_for_operation": usable,
            "reason": attempt.get("exception_message", "") or ",".join(raw.quality_issues),
            "from_cache": attempt.get("from_cache", ""),
            "call_id": attempt.get("call_id", ""),
            "call_count": attempt.get("call_count", ""),
            "cache_hits": attempt.get("cache_hits", ""),
            "returned_rows": attempt.get("returned_rows", ""),
            "category": attempt.get("category", ""),
            "provider_status": attempt.get("provider_status", ""),
            "elapsed_seconds_first_call": attempt.get("elapsed_seconds_first_call", ""),
            "secid": attempt.get("secid", diagnostics.get("secid", "")),
            "endpoint": attempt.get("endpoint", diagnostics.get("endpoint", "")),
            "request_status": attempt.get("request_status", diagnostics.get("request_status", "")),
            "retry_count": attempt.get("retry_count", diagnostics.get("retry_count", "")),
            "final_status": attempt.get("final_status", diagnostics.get("final_status", "")),
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
    elapsed_seconds: float | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, object]:
    elapsed = round(elapsed_seconds or 0.0, 3)
    timeout = float(timeout_seconds or 0.0)
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
        "elapsed_seconds": elapsed,
        "timeout_seconds": timeout,
        "slow_provider_attempt": bool(timeout and elapsed > timeout),
    }


def _stamp_elapsed(attempts: list[dict[str, object]], elapsed_seconds: float, timeout_seconds: float) -> list[dict[str, object]]:
    elapsed = round(elapsed_seconds, 3)
    return [
        {
            **attempt,
            "elapsed_seconds": elapsed,
            "timeout_seconds": timeout_seconds,
            "slow_provider_attempt": elapsed_seconds > timeout_seconds,
        }
        for attempt in attempts
    ]


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


def _policy_priority(instrument: Instrument, stock_chain: list[str], quote_purpose: str = "operation") -> list[str]:
    if instrument.symbol == "GOLD_CNY" or instrument.provider == "manual":
        return ["manual"]
    if instrument.symbol in ENERGY_A_SHARE_SYMBOLS | HK_SYMBOLS:
        if quote_purpose == "reference" and instrument.symbol in EASTMONEY_DIRECT_SYMBOLS:
            return list(dict.fromkeys(["eastmoney_direct", *stock_chain]))
        return stock_chain
    if instrument.symbol in ETF_SYMBOLS:
        if quote_purpose == "reference":
            return ["eastmoney_direct", "yfinance", "akshare", "mock"]
        return ["akshare", "mock"]
    return [provider for provider in (instrument.provider_priority or [instrument.provider]) if provider != "disabled"]


def _diagnostic_priority(instrument: Instrument, configured_priority: list[str], quote_purpose: str) -> list[str]:
    if instrument.symbol == "GOLD_CNY" or instrument.provider == "manual":
        return ["manual"]
    base = configured_priority or _policy_priority(instrument, ["akshare", "yfinance", "mock"], quote_purpose=quote_purpose)
    if instrument.symbol in EASTMONEY_DIRECT_SYMBOLS:
        return list(dict.fromkeys(["eastmoney_direct", *base, "akshare", "yfinance", "mock"]))
    return base


def _skipped_after_success(symbol: str, priority: list[str], selected_provider: str, provider_policy: str, quote_purpose: str = "operation") -> list[dict[str, object]]:
    if selected_provider not in priority:
        return []
    skip_reason = f"selected_provider_success_policy_skip:{provider_policy}"
    if quote_purpose == "reference" and selected_provider == "eastmoney_direct" and symbol in EASTMONEY_DIRECT_SYMBOLS:
        skip_reason = "skipped because eastmoney_direct reference quote succeeded in reference mode"
    elif quote_purpose == "reference" and selected_provider == "yfinance" and symbol in ETF_SYMBOLS:
        skip_reason = "skipped because yfinance reference quote succeeded in reference mode"
    return [
        _attempt(
            symbol,
            provider,
            "skipped",
            reason=skip_reason,
            elapsed_seconds=0.0,
        )
        for provider in priority[priority.index(selected_provider) + 1 :]
    ]
