from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import time as time_module
from typing import Any, Callable

import pandas as pd

from market_price_guard.freshness import now_utc
from market_price_guard.models import RawPrice
from market_price_guard.providers.base import PriceProvider


A_STOCK_SYMBOLS = {"601899.SH", "601985.SH", "003816.SZ"}
HK_STOCK_SYMBOLS = {"00883.HK"}
ETF_SYMBOLS = {"159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"}
SHANGHAI_TZ = timezone(timedelta(hours=8))

CODE_COLUMNS = ["代码", "证券代码", "股票代码", "基金代码", "symbol", "code"]
NAME_COLUMNS = ["名称", "股票简称", "基金简称", "基金名称", "简称", "name"]
PRICE_COLUMNS = ["最新价", "最新", "现价", "收盘", "价格", "price", "最新价格"]
QUOTE_TIME_COLUMNS = ["更新时间", "update_time", "quote_time", "时间", "数据时间", "数据日期"]


class AkshareProvider(PriceProvider):
    def __init__(self, ak_module: Any | None = None):
        self.ak_module = ak_module
        self._call_cache: dict[str, tuple[pd.DataFrame | None, dict[str, object]]] = {}
        self._call_seq = 0

    def fetch(self, symbols: list[str]) -> dict[str, RawPrice]:
        fetch_time = now_utc()
        if not symbols:
            return {}
        try:
            ak = self.ak_module or _import_akshare()
        except ImportError as exc:
            return {
                symbol: _error_price(
                    symbol=symbol,
                    fetch_time=fetch_time,
                    quality_issues=["akshare_not_installed", "provider_error"],
                    function_name="import_akshare",
                    category=_category_for_symbol(symbol),
                    exception=exc,
                    provider_status="failed",
                )
                for symbol in symbols
            }

        prices: dict[str, RawPrice] = {}
        prices.update(self._fetch_a_shares(ak, [s for s in symbols if s in A_STOCK_SYMBOLS], fetch_time))
        prices.update(self._fetch_hk_shares(ak, [s for s in symbols if s in HK_STOCK_SYMBOLS], fetch_time))
        prices.update(
            self._fetch_single_interface(
                ak=ak,
                symbols=[s for s in symbols if s in ETF_SYMBOLS],
                currency="CNY",
                fetch_time=fetch_time,
                function_name="fund_etf_spot_em",
                category="ETF",
            )
        )

        for symbol in symbols:
            if symbol not in prices:
                prices[symbol] = _error_price(
                    symbol=symbol,
                    fetch_time=fetch_time,
                    quality_issues=["symbol_not_found"],
                    function_name="unknown",
                    category=_category_for_symbol(symbol),
                    provider_status="failed",
                )
        return prices

    def _fetch_a_shares(self, ak: Any, symbols: list[str], fetch_time: datetime) -> dict[str, RawPrice]:
        if not symbols:
            return {}

        primary_df, primary_attempt = self._call_akshare_cached(ak, "stock_zh_a_spot_em", "A_SHARE", fetch_time)
        if primary_df is not None:
            return self._rows_to_prices(
                symbols=symbols,
                df=primary_df,
                currency="CNY",
                fetch_time=fetch_time,
                function_name="stock_zh_a_spot_em",
                category="A_SHARE",
                provider_status="success",
                attempts=[primary_attempt],
            )

        prices: dict[str, RawPrice] = {}
        fallback_groups = [
            ("stock_sh_a_spot_em", [symbol for symbol in symbols if symbol.endswith(".SH")]),
            ("stock_sz_a_spot_em", [symbol for symbol in symbols if symbol.endswith(".SZ")]),
        ]
        for function_name, group_symbols in fallback_groups:
            if not group_symbols:
                continue
            fallback_df, fallback_attempt = self._call_akshare_cached(ak, function_name, "A_SHARE", fetch_time)
            attempts = [primary_attempt, fallback_attempt]
            if fallback_df is not None:
                prices.update(
                    self._rows_to_prices(
                        symbols=group_symbols,
                        df=fallback_df,
                        currency="CNY",
                        fetch_time=fetch_time,
                        function_name=function_name,
                        category="A_SHARE",
                        provider_status="fallback_success",
                        attempts=attempts,
                    )
                )
            else:
                for symbol in group_symbols:
                    prices[symbol] = _error_price(
                        symbol=symbol,
                        fetch_time=fetch_time,
                        quality_issues=["provider_error"],
                        currency="CNY",
                        function_name=function_name,
                        category="A_SHARE",
                        exception=fallback_attempt.get("_exception"),
                        diagnostics={"attempts": [_public_attempt(attempt) for attempt in attempts]},
                        provider_status="fallback_failed",
                    )
        return prices

    def _fetch_hk_shares(self, ak: Any, symbols: list[str], fetch_time: datetime) -> dict[str, RawPrice]:
        if not symbols:
            return {}

        attempts: list[dict[str, object]] = []
        for index, function_name in enumerate(
            ["stock_hk_spot_em", "stock_hk_main_board_spot_em", "stock_hsgt_sh_hk_spot_em"]
        ):
            df, attempt = self._call_akshare_cached(ak, function_name, "HK", fetch_time)
            attempts.append(attempt)
            if df is None:
                continue
            return self._rows_to_prices(
                symbols=symbols,
                df=df,
                currency="HKD",
                fetch_time=fetch_time,
                function_name=function_name,
                category="HK",
                provider_status="success" if index == 0 else "fallback_success",
                attempts=attempts,
            )

        last_attempt = attempts[-1]
        return {
            symbol: _error_price(
                symbol=symbol,
                fetch_time=fetch_time,
                quality_issues=["provider_error"],
                currency="HKD",
                function_name=str(last_attempt["function_name"]),
                category="HK",
                exception=last_attempt.get("_exception"),
                diagnostics={"attempts": [_public_attempt(attempt) for attempt in attempts]},
                provider_status="fallback_failed",
            )
            for symbol in symbols
        }

    def _fetch_single_interface(
        self,
        ak: Any,
        symbols: list[str],
        currency: str,
        fetch_time: datetime,
        function_name: str,
        category: str,
    ) -> dict[str, RawPrice]:
        if not symbols:
            return {}
        df, attempt = self._call_akshare_cached(ak, function_name, category, fetch_time)
        if df is None:
            return {
                symbol: _error_price(
                    symbol=symbol,
                    fetch_time=fetch_time,
                    quality_issues=["provider_error"],
                    currency=currency,
                    function_name=function_name,
                    category=category,
                    exception=attempt.get("_exception"),
                    diagnostics={"attempts": [_public_attempt(attempt)]},
                    provider_status="failed",
                )
                for symbol in symbols
            }
        return self._rows_to_prices(
            symbols=symbols,
            df=df,
            currency=currency,
            fetch_time=fetch_time,
            function_name=function_name,
            category=category,
            provider_status="success",
            attempts=[attempt],
        )

    def _rows_to_prices(
        self,
        symbols: list[str],
        df: pd.DataFrame,
        currency: str,
        fetch_time: datetime,
        function_name: str,
        category: str,
        provider_status: str,
        attempts: list[dict[str, object]],
    ) -> dict[str, RawPrice]:
        matched_symbols = [symbol for symbol in symbols if _find_row(symbol, df) is not None]
        attempts[-1]["matched_symbols"] = matched_symbols
        diagnostics = {
            "provider": "akshare",
            "function_name": function_name,
            "category": category,
            "status": "success",
            "provider_status": provider_status,
            "returned_rows": 0 if df is None else len(df),
            "matched_symbols": matched_symbols,
            "attempts": [_public_attempt(attempt) for attempt in attempts],
            "fetch_time_utc": fetch_time.isoformat(),
        }
        return {
            symbol: self._row_to_price(symbol, df, currency, fetch_time, diagnostics)
            for symbol in symbols
        }

    def _row_to_price(
        self,
        symbol: str,
        df: pd.DataFrame,
        currency: str,
        fetch_time: datetime,
        diagnostics: dict[str, object],
    ) -> RawPrice:
        row = _find_row(symbol, df)
        if row is None:
            return _error_price(
                symbol=symbol,
                fetch_time=fetch_time,
                quality_issues=["symbol_not_found"],
                currency=currency,
                function_name=str(diagnostics["function_name"]),
                category=str(diagnostics["category"]),
                diagnostics=diagnostics,
                provider_status=str(diagnostics.get("provider_status", "failed")),
            )

        issues: list[str] = []
        price = _extract_positive_price(row)
        if price is None:
            issues.append("invalid_price")
        quote_time, quote_issues, quote_raw = _extract_quote_time(row)
        issues.extend(quote_issues)

        row_diagnostics = {
            **diagnostics,
            "symbol": symbol,
            "price": price if price is not None else "",
            "quote_time": quote_time.isoformat() if quote_time else "",
            "quote_time_raw": quote_raw or "",
            "quote_time_utc": quote_time.astimezone(timezone.utc).isoformat() if quote_time else "",
            "fetch_time_utc": fetch_time.isoformat(),
        }

        return RawPrice(
            symbol=symbol,
            name=_extract_text(row, NAME_COLUMNS) or symbol,
            market=_market_for_symbol(symbol),
            price=price,
            currency=currency,
            source="akshare",
            quote_time=quote_time,
            fetch_time=fetch_time,
            market_status=_market_status_for_symbol(symbol, quote_time or fetch_time),
            quality_issues=issues,
            provider_diagnostics=row_diagnostics,
        )

    def _call_akshare_cached(
        self,
        ak: Any,
        function_name: str,
        category: str,
        fetch_time: datetime,
    ) -> tuple[pd.DataFrame | None, dict[str, object]]:
        if function_name in self._call_cache:
            df, cached_attempt = self._call_cache[function_name]
            attempt = dict(cached_attempt)
            attempt["from_cache"] = True
            attempt["cache_hits"] = int(attempt.get("cache_hits", 0)) + 1
            attempt["fetch_time_utc"] = fetch_time.isoformat()
            if "_exception" in cached_attempt:
                attempt["_exception"] = cached_attempt["_exception"]
            return df, attempt

        self._call_seq += 1
        df, attempt = _call_akshare(ak, function_name, category, fetch_time, call_id=self._call_seq)
        attempt["from_cache"] = False
        attempt["cache_hits"] = 0
        attempt["call_count"] = 1
        self._call_cache[function_name] = (df, dict(attempt))
        return df, attempt


def _import_akshare() -> Any:
    try:
        import akshare as ak
    except ImportError as exc:
        raise ImportError("akshare_not_installed") from exc
    return ak


def _call_akshare(ak: Any, function_name: str, category: str, fetch_time: datetime, call_id: int) -> tuple[pd.DataFrame | None, dict[str, object]]:
    attempt = {
        "provider": "akshare",
        "function_name": function_name,
        "category": category,
        "fetch_time_utc": fetch_time.isoformat(),
        "call_id": call_id,
    }
    start = time_module.perf_counter()
    try:
        fetch_fn: Callable[[], pd.DataFrame] = getattr(ak, function_name)
        df = fetch_fn()
    except Exception as exc:
        elapsed = time_module.perf_counter() - start
        attempt.update(
            {
                "status": "fail",
                "provider_status": "failed",
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "_exception": exc,
                "elapsed_seconds_first_call": round(elapsed, 3),
            }
        )
        return None, attempt

    elapsed = time_module.perf_counter() - start
    attempt.update(
        {
            "status": "success",
            "provider_status": "success",
            "returned_rows": 0 if df is None else len(df),
            "matched_symbols": [],
            "elapsed_seconds_first_call": round(elapsed, 3),
        }
    )
    return df, attempt


def _public_attempt(attempt: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in attempt.items() if key != "_exception"}


def _find_row(symbol: str, df: pd.DataFrame) -> pd.Series | None:
    if df is None or df.empty:
        return None
    target_codes = _candidate_codes(symbol)
    for column in CODE_COLUMNS:
        if column not in df.columns:
            continue
        normalized = df[column].map(_normalize_code)
        mask = normalized.isin(target_codes)
        if mask.any():
            return df.loc[mask].iloc[0]
    return None


def _candidate_codes(symbol: str) -> set[str]:
    base = symbol.split(".")[0]
    candidates = {base, base.lstrip("0")}
    if symbol.endswith(".HK"):
        candidates.add(base.zfill(5))
    return {candidate for candidate in candidates if candidate}


def _normalize_code(value: Any) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _extract_positive_price(row: pd.Series) -> float | None:
    for column in PRICE_COLUMNS:
        if column not in row:
            continue
        try:
            price = float(row[column])
        except (TypeError, ValueError):
            continue
        if price > 0:
            return price
        return None
    return None


def _extract_text(row: pd.Series, columns: list[str]) -> str | None:
    for column in columns:
        if column in row and pd.notna(row[column]):
            return str(row[column])
    return None


def _extract_quote_time(row: pd.Series) -> tuple[datetime | None, list[str], str | None]:
    for column in QUOTE_TIME_COLUMNS:
        if column not in row or pd.isna(row[column]):
            continue
        raw_value = str(row[column]).strip()
        if not raw_value:
            continue
        parsed = _parse_quote_time(raw_value)
        if parsed is None:
            return None, ["invalid_quote_time"], raw_value
        issues: list[str] = []
        if column == "数据日期" and len(raw_value) <= 10:
            issues.append("quote_time_date_only")
            issues.append("low_precision_quote_time")
        elif parsed.tzinfo is None:
            issues.append("assumed_timezone_asia_shanghai")
            parsed = parsed.replace(tzinfo=SHANGHAI_TZ)
        return _ensure_aware_shanghai(parsed), issues, raw_value
    return None, ["quote_time_missing"], None


def _parse_quote_time(value: str) -> datetime | None:
    normalized = value.replace("/", "-")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        try:
            return datetime.strptime(normalized, "%Y-%m-%d")
        except ValueError:
            return None


def _ensure_aware_shanghai(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=SHANGHAI_TZ)


def _market_for_symbol(symbol: str) -> str:
    if symbol.endswith(".HK"):
        return "HK"
    return "CN"


def _market_status_for_symbol(symbol: str, reference_time: datetime) -> str:
    local_time = _ensure_aware_shanghai(reference_time).astimezone(SHANGHAI_TZ).time()
    if symbol.endswith(".HK"):
        return "open" if _in_ranges(local_time, [(time(9, 30), time(12, 0)), (time(13, 0), time(16, 0))]) else "closed"
    if symbol.endswith((".SH", ".SZ")):
        return "open" if _in_ranges(local_time, [(time(9, 30), time(11, 30)), (time(13, 0), time(15, 0))]) else "closed"
    return "unknown"


def _in_ranges(value: time, ranges: list[tuple[time, time]]) -> bool:
    return any(start <= value < end for start, end in ranges)


def _category_for_symbol(symbol: str) -> str:
    if symbol in A_STOCK_SYMBOLS:
        return "A_SHARE"
    if symbol in HK_STOCK_SYMBOLS:
        return "HK"
    if symbol in ETF_SYMBOLS:
        return "ETF"
    return "UNKNOWN"


def _error_price(
    symbol: str,
    fetch_time: datetime,
    quality_issues: list[str],
    function_name: str,
    category: str,
    currency: str = "",
    exception: Exception | None = None,
    diagnostics: dict[str, object] | None = None,
    provider_status: str = "failed",
) -> RawPrice:
    provider_diagnostics = {
        "provider": "akshare",
        "function_name": function_name,
        "symbol": symbol,
        "category": category,
        "status": "fail" if "provider_error" in quality_issues or "akshare_not_installed" in quality_issues else "success",
        "provider_status": provider_status,
        "fetch_time_utc": fetch_time.isoformat(),
    }
    if diagnostics:
        provider_diagnostics.update(diagnostics)
        provider_diagnostics["symbol"] = symbol
        provider_diagnostics["provider_status"] = provider_status
    if exception is not None:
        provider_diagnostics["exception_type"] = type(exception).__name__
        provider_diagnostics["exception_message"] = str(exception)

    return RawPrice(
        symbol=symbol,
        price=None,
        currency=currency,
        source="akshare",
        quote_time=None,
        fetch_time=fetch_time,
        market_status="unknown",
        quality_issues=quality_issues,
        provider_diagnostics=provider_diagnostics,
    )
