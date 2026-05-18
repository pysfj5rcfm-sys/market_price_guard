from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any

import pandas as pd

from market_price_guard.freshness import now_utc
from market_price_guard.models import RawPrice
from market_price_guard.providers.base import PriceProvider


SUPPORTED_SYMBOLS = {"00883.HK", "883.HK"}
HONG_KONG_TZ = timezone(timedelta(hours=8))


class YFinanceProvider(PriceProvider):
    def __init__(self, yf_module: Any | None = None):
        self.yf_module = yf_module

    def fetch(self, symbols: list[str]) -> dict[str, RawPrice]:
        fetch_time = now_utc()
        try:
            yf = self.yf_module or _import_yfinance()
        except ImportError as exc:
            return {
                symbol: _error_price(symbol, fetch_time, ["yfinance_not_installed", "provider_error"], exception=exc)
                for symbol in symbols
            }

        prices: dict[str, RawPrice] = {}
        for symbol in symbols:
            if symbol not in SUPPORTED_SYMBOLS:
                continue
            prices[_internal_symbol(symbol)] = self._fetch_symbol(yf, symbol, fetch_time)
        return prices

    def _fetch_symbol(self, yf: Any, symbol: str, fetch_time: datetime) -> RawPrice:
        internal_symbol = _internal_symbol(symbol)
        yahoo_ticker = yahoo_ticker_for_symbol(symbol)
        diagnostics = {
            "provider": "yfinance",
            "function_name": "yfinance.Ticker",
            "symbol": internal_symbol,
            "yahoo_ticker": yahoo_ticker,
            "category": "HK",
            "fetch_time_utc": fetch_time.isoformat(),
            "source_limit_note": _source_limit_note(),
        }
        try:
            ticker = yf.Ticker(yahoo_ticker)
            fast_info = _as_mapping(getattr(ticker, "fast_info", {}) or {})
            history_result = _history_price(ticker)
        except Exception as exc:
            return _error_price(internal_symbol, fetch_time, ["provider_error"], exception=exc, diagnostics=diagnostics)

        issues: list[str] = []
        price = _positive_float(_first_present(fast_info, ["last_price", "lastPrice", "last_price"]))
        currency = _text(_first_present(fast_info, ["currency"]))
        quote_time = _parse_quote_time(_first_present(fast_info, ["last_trade_time", "lastTradeTime", "regularMarketTime"]))
        quote_time_raw = quote_time.isoformat() if quote_time else ""

        if price is None and history_result.price is not None:
            price = history_result.price
        if quote_time is None and history_result.quote_time is not None:
            quote_time = history_result.quote_time
            quote_time_raw = history_result.quote_time_raw
            issues.extend(history_result.quality_issues)

        if price is None:
            issues.append("invalid_price")
        if not currency:
            currency = "HKD"
            issues.append("assumed_currency_hkd")
        if quote_time is None:
            issues.append("quote_time_missing")

        diagnostics.update(
            {
                "status": "success" if "provider_error" not in issues else "fail",
                "provider_status": "success",
                "price": price if price is not None else "",
                "quote_time": quote_time.isoformat() if quote_time else "",
                "quote_time_raw": quote_time_raw,
                "quote_time_utc": quote_time.astimezone(timezone.utc).isoformat() if quote_time else "",
                "currency": currency,
                "attempts": [
                    {
                        "provider": "yfinance",
                        "function_name": "yfinance.Ticker",
                        "category": "HK",
                        "status": "success" if price is not None and quote_time is not None else "fail",
                        "provider_status": "success" if price is not None and quote_time is not None else "failed",
                        "matched_symbols": [internal_symbol] if price is not None else [],
                        "fetch_time_utc": fetch_time.isoformat(),
                    }
                ],
            }
        )

        return RawPrice(
            symbol=internal_symbol,
            name="中海油H",
            market="HK",
            price=price,
            currency=currency,
            source="yfinance",
            quote_time=quote_time,
            fetch_time=fetch_time,
            market_status=_hk_market_status(quote_time or fetch_time),
            quality_issues=list(dict.fromkeys(issues)),
            provider_diagnostics=diagnostics,
        )


class HistoryResult:
    def __init__(
        self,
        price: float | None = None,
        quote_time: datetime | None = None,
        quote_time_raw: str = "",
        quality_issues: list[str] | None = None,
    ):
        self.price = price
        self.quote_time = quote_time
        self.quote_time_raw = quote_time_raw
        self.quality_issues = quality_issues or []


def yahoo_ticker_for_symbol(symbol: str) -> str:
    base = symbol.split(".")[0].lstrip("0") or "0"
    if symbol.endswith(".HK"):
        return f"{base.zfill(4)}.HK"
    raise ValueError(f"unsupported yfinance symbol: {symbol}")


def _import_yfinance() -> Any:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError("yfinance_not_installed") from exc
    return yf


def _history_price(ticker: Any) -> HistoryResult:
    minute = _history_from_frame(ticker.history(period="1d", interval="1m"), daily=False)
    if minute.price is not None or minute.quote_time is not None:
        return minute
    return _history_from_frame(ticker.history(period="5d", interval="1d"), daily=True)


def _history_from_frame(frame: Any, daily: bool) -> HistoryResult:
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty or "Close" not in frame:
        return HistoryResult()
    valid = frame[pd.notna(frame["Close"])]
    if valid.empty:
        return HistoryResult()
    last_index = valid.index[-1]
    price = _positive_float(valid["Close"].iloc[-1])
    quote_time = _parse_quote_time(last_index)
    issues = ["daily_close_only", "low_precision_quote_time"] if daily and quote_time is not None else []
    return HistoryResult(price=price, quote_time=quote_time, quote_time_raw=str(last_index), quality_issues=issues)


def _parse_quote_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=HONG_KONG_TZ)
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("/", "-"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=HONG_KONG_TZ)
        return parsed
    return None


def _hk_market_status(reference_time: datetime) -> str:
    local_time = _parse_quote_time(reference_time)
    if local_time is None:
        return "unknown"
    current = local_time.astimezone(HONG_KONG_TZ).time()
    is_open = (time(9, 30) <= current < time(12, 0)) or (time(13, 0) <= current < time(16, 0))
    return "open" if is_open else "closed"


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    result: dict[str, Any] = {}
    for key in ["last_price", "lastPrice", "currency", "last_trade_time", "lastTradeTime", "regularMarketTime"]:
        try:
            result[key] = value[key]
        except Exception:
            try:
                result[key] = getattr(value, key)
            except Exception:
                continue
    return result


def _first_present(mapping: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def _positive_float(value: Any) -> float | None:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None
    return price


def _text(value: Any) -> str:
    return "" if value in (None, "") else str(value)


def _internal_symbol(symbol: str) -> str:
    return "00883.HK" if symbol in SUPPORTED_SYMBOLS else symbol


def _source_limit_note() -> str:
    return "yfinance is an open-source Yahoo Finance public API wrapper for research/educational use; not an official exchange feed"


def _error_price(
    symbol: str,
    fetch_time: datetime,
    quality_issues: list[str],
    exception: Exception | None = None,
    diagnostics: dict[str, object] | None = None,
) -> RawPrice:
    provider_diagnostics = {
        "provider": "yfinance",
        "function_name": "yfinance.Ticker",
        "symbol": _internal_symbol(symbol),
        "category": "HK",
        "status": "fail",
        "provider_status": "failed",
        "fetch_time_utc": fetch_time.isoformat(),
        "source_limit_note": _source_limit_note(),
    }
    if diagnostics:
        provider_diagnostics.update(diagnostics)
    if exception is not None:
        provider_diagnostics["exception_type"] = type(exception).__name__
        provider_diagnostics["exception_message"] = str(exception)
    return RawPrice(
        symbol=_internal_symbol(symbol),
        name="中海油H",
        market="HK",
        price=None,
        currency="HKD",
        source="yfinance",
        quote_time=None,
        fetch_time=fetch_time,
        market_status="unknown",
        quality_issues=quality_issues,
        provider_diagnostics=provider_diagnostics,
    )
