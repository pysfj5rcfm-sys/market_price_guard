from __future__ import annotations

import json
import time
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from market_price_guard.freshness import now_utc
from market_price_guard.models import RawPrice
from market_price_guard.providers.base import PriceProvider


SHANGHAI_TZ = timezone(timedelta(hours=8))
BASE_URL = "https://push2.eastmoney.com/api/qt/stock/get"
FALLBACK_URLS = ["https://push2.eastmoney.com/api/qt/stock/get", "http://push2.eastmoney.com/api/qt/stock/get"]
FUNCTION_NAME = "eastmoney_direct.stock_get"
FIELDS = "f43,f57,f58,f60,f44,f45,f46,f47,f48,f86,f170,f169"
SUPPORTED_SYMBOLS = {
    "159632.SZ",
    "513300.SH",
    "159819.SZ",
    "515880.SH",
    "510300.SH",
    "601899.SH",
    "601985.SH",
    "003816.SZ",
}
SYMBOL_NAMES = {
    "159632.SZ": "纳指相关ETF",
    "513300.SH": "纳指ETF",
    "159819.SZ": "人工智能ETF",
    "515880.SH": "通信ETF",
    "510300.SH": "沪深300ETF",
    "601899.SH": "紫金矿业A",
    "601985.SH": "中国核电",
    "003816.SZ": "中国广核",
}
SOURCE_LIMIT_NOTE = (
    "Eastmoney Direct uses Eastmoney public web quote endpoint; not an official exchange real-time feed; "
    "first version is reference-grade / operation-candidate only"
)


class EastmoneyDirectProvider(PriceProvider):
    def __init__(self, http_get: Any | None = None, base_url: str = BASE_URL, timeout_seconds: float = 5.0, max_retries: int = 1):
        self.http_get = http_get or _default_http_get
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def fetch(self, symbols: list[str]) -> dict[str, RawPrice]:
        fetch_time = now_utc()
        prices: dict[str, RawPrice] = {}
        for symbol in symbols:
            if symbol not in SUPPORTED_SYMBOLS:
                continue
            prices[symbol] = self._fetch_symbol(symbol, fetch_time)
        return prices

    def _fetch_symbol(self, symbol: str, fetch_time: datetime) -> RawPrice:
        try:
            secid = eastmoney_secid_for_symbol(symbol)
        except ValueError as exc:
            return _error_price(symbol, fetch_time, ["provider_error"], exception=exc)

        params = {
            "secid": secid,
            "fields": FIELDS,
            "fltt": "2",
            "invt": "2",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "_": str(int(time.time() * 1000)),
        }
        endpoints = list(dict.fromkeys([self.base_url, *FALLBACK_URLS]))
        diagnostics = _base_diagnostics(symbol, fetch_time, secid, endpoint=self.base_url)
        payload: dict[str, Any] | None = None
        last_exception: Exception | None = None
        attempts_made = 0
        for endpoint in endpoints:
            for retry_index in range(self.max_retries + 1):
                attempts_made += 1
                diagnostics.update({"endpoint": endpoint, "request_status": "attempting", "retry_count": retry_index})
                try:
                    payload = _as_payload(self.http_get(endpoint, params, self.timeout_seconds))
                    diagnostics.update({"endpoint": endpoint, "request_status": "success", "retry_count": retry_index, "final_status": "success"})
                    break
                except TypeError:
                    try:
                        payload = _as_payload(self.http_get(endpoint, params))
                        diagnostics.update({"endpoint": endpoint, "request_status": "success", "retry_count": retry_index, "final_status": "success"})
                        break
                    except Exception as exc:
                        last_exception = exc
                except Exception as exc:
                    last_exception = exc
                diagnostics.update(
                    {
                        "endpoint": endpoint,
                        "request_status": "failed",
                        "retry_count": retry_index,
                        "final_status": "failed",
                        "exception_type": type(last_exception).__name__ if last_exception else "",
                        "exception_message": str(last_exception) if last_exception else "",
                    }
                )
            if payload is not None:
                break
        diagnostics["attempt_count"] = attempts_made
        if payload is None:
            return _error_price(symbol, fetch_time, ["provider_error"], exception=last_exception, diagnostics=diagnostics)

        rc = payload.get("rc")
        data = payload.get("data")
        if rc not in (0, "0", None):
            return _error_price(symbol, fetch_time, ["provider_error"], diagnostics={**diagnostics, "exception_type": "EastmoneyRcError", "exception_message": f"rc={rc}"})
        if not isinstance(data, dict) or not data:
            return _error_price(symbol, fetch_time, ["provider_error"], diagnostics={**diagnostics, "exception_type": "EastmoneyEmptyData", "exception_message": "data empty"})

        issues: list[str] = []
        price = _positive_float(data.get("f43"))
        if price is None:
            issues.append("invalid_price")
        quote_time = _parse_f86(data.get("f86"))
        if quote_time is None:
            issues.append("quote_time_missing")
        currency = "CNY"
        issues.append("assumed_currency_cny")
        name = str(data.get("f58") or SYMBOL_NAMES.get(symbol, symbol))
        code = str(data.get("f57") or symbol.split(".")[0])

        diagnostics.update(
            {
                "status": "success" if price is not None and quote_time is not None else "fail",
                "provider_status": "success" if price is not None and quote_time is not None else "failed",
                "price": price if price is not None else "",
                "currency": currency,
                "code": code,
                "quote_time": quote_time.isoformat() if quote_time else "",
                "quote_time_raw": data.get("f86", ""),
                "quote_time_utc": quote_time.astimezone(timezone.utc).isoformat() if quote_time else "",
                "reference_note": SOURCE_LIMIT_NOTE,
                "attempts": [
                    {
                        "provider": "eastmoney_direct",
                        "function_name": FUNCTION_NAME,
                        "category": _category_for_symbol(symbol),
                        "status": "success" if price is not None and quote_time is not None else "fail",
                        "provider_status": "success" if price is not None and quote_time is not None else "failed",
                        "matched_symbols": [symbol] if price is not None else [],
                        "affected_symbols": [symbol],
                        "secid": secid,
                        "endpoint": diagnostics.get("endpoint", ""),
                        "request_status": diagnostics.get("request_status", ""),
                        "retry_count": diagnostics.get("retry_count", 0),
                        "final_status": diagnostics.get("final_status", ""),
                        "fetch_time_utc": fetch_time.isoformat(),
                    }
                ],
            }
        )

        return RawPrice(
            symbol=symbol,
            name=name,
            market="CN",
            price=price,
            currency=currency,
            source="eastmoney_direct",
            quote_time=quote_time,
            fetch_time=fetch_time,
            market_status=_market_status(quote_time or fetch_time),
            quality_issues=list(dict.fromkeys(issues)),
            provider_diagnostics=diagnostics,
            quote_trust_tier="reference",
            usable_for_reference=price is not None and quote_time is not None,
            confirmation_required=True,
            operation_blocking_reason="reference_tier_requires_operation_confirmation",
            reference_note=SOURCE_LIMIT_NOTE,
        )


def eastmoney_secid_for_symbol(symbol: str) -> str:
    code, sep, suffix = symbol.partition(".")
    if not sep or not code:
        raise ValueError(f"unsupported eastmoney symbol: {symbol}")
    if suffix == "SH":
        return f"1.{code}"
    if suffix == "SZ":
        return f"0.{code}"
    raise ValueError(f"unsupported eastmoney market: {symbol}")


def _default_http_get(url: str, params: dict[str, str], timeout_seconds: float = 5.0) -> dict[str, Any]:
    request = Request(f"{url}?{urlencode(params)}", headers=_eastmoney_headers())
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _eastmoney_headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) market_price_guard/0.7",
        "Referer": "https://quote.eastmoney.com/",
        "Accept": "application/json,text/plain,*/*",
        "Connection": "close",
    }


def _as_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("invalid eastmoney response payload")


def _positive_float(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None
    return price


def _parse_f86(value: Any) -> datetime | None:
    if value in (None, "", "-", 0, "0"):
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    if timestamp > 10_000_000_000:
        timestamp = timestamp / 1000
    try:
        return datetime.fromtimestamp(timestamp, tz=SHANGHAI_TZ)
    except (OSError, OverflowError, ValueError):
        return None


def _market_status(reference_time: datetime) -> str:
    local = reference_time.astimezone(SHANGHAI_TZ).time()
    is_open = (dt_time(9, 30) <= local < dt_time(11, 30)) or (dt_time(13, 0) <= local < dt_time(15, 0))
    return "open" if is_open else "closed"


def _category_for_symbol(symbol: str) -> str:
    if symbol in {"159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"}:
        return "ETF"
    return "A_SHARE"


def _base_diagnostics(symbol: str, fetch_time: datetime, secid: str, endpoint: str = BASE_URL) -> dict[str, object]:
    return {
        "provider": "eastmoney_direct",
        "function_name": FUNCTION_NAME,
        "symbol": symbol,
        "secid": secid,
        "endpoint": endpoint,
        "request_status": "",
        "retry_count": 0,
        "final_status": "",
        "category": _category_for_symbol(symbol),
        "fetch_time_utc": fetch_time.isoformat(),
        "quote_trust_tier": "reference",
        "usable_for_operation": False,
        "confirmation_required": True,
        "source_limit_note": SOURCE_LIMIT_NOTE,
    }


def _error_price(
    symbol: str,
    fetch_time: datetime,
    quality_issues: list[str],
    exception: Exception | None = None,
    diagnostics: dict[str, object] | None = None,
) -> RawPrice:
    secid = ""
    try:
        secid = eastmoney_secid_for_symbol(symbol)
    except ValueError:
        pass
    provider_diagnostics = _base_diagnostics(symbol, fetch_time, secid)
    if diagnostics:
        provider_diagnostics.update(diagnostics)
    if exception is not None:
        provider_diagnostics["exception_type"] = type(exception).__name__
        provider_diagnostics["exception_message"] = str(exception)
    provider_diagnostics.update(
        {
            "status": "fail",
            "provider_status": "failed",
            "attempts": [
                {
                    "provider": "eastmoney_direct",
                    "function_name": FUNCTION_NAME,
                    "category": _category_for_symbol(symbol) if symbol in SUPPORTED_SYMBOLS else "",
                    "status": "fail",
                    "provider_status": "failed",
                    "matched_symbols": [],
                    "affected_symbols": [symbol],
                    "secid": secid,
                    "endpoint": provider_diagnostics.get("endpoint", ""),
                    "request_status": provider_diagnostics.get("request_status", "failed"),
                    "retry_count": provider_diagnostics.get("retry_count", 0),
                    "final_status": provider_diagnostics.get("final_status", "failed"),
                    "exception_type": provider_diagnostics.get("exception_type", ""),
                    "exception_message": provider_diagnostics.get("exception_message", ""),
                    "fetch_time_utc": fetch_time.isoformat(),
                }
            ],
        }
    )
    return RawPrice(
        symbol=symbol,
        name=SYMBOL_NAMES.get(symbol, symbol),
        market="CN",
        price=None,
        currency="CNY",
        source="eastmoney_direct",
        quote_time=None,
        fetch_time=fetch_time,
        market_status="unknown",
        quality_issues=list(dict.fromkeys(quality_issues)),
        provider_diagnostics=provider_diagnostics,
        quote_trust_tier="reference",
        usable_for_reference=False,
        confirmation_required=True,
        operation_blocking_reason="reference_tier_requires_operation_confirmation",
        reference_note=SOURCE_LIMIT_NOTE,
    )
