from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from market_price_guard.freshness import now_utc
from market_price_guard.models import RawPrice
from market_price_guard.providers.base import PriceProvider


A_STOCK_SYMBOLS = {"601899.SH", "601985.SH", "003816.SZ"}
HK_STOCK_SYMBOLS = {"00883.HK"}
ETF_SYMBOLS = {"159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"}
SHANGHAI_TZ = timezone(timedelta(hours=8))


class AkshareProvider(PriceProvider):
    def __init__(self, ak_module: Any | None = None):
        self.ak_module = ak_module

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
                )
                for symbol in symbols
            }

        groups = [
            ("stock_zh_a_spot_em", "A_SHARE", [s for s in symbols if s in A_STOCK_SYMBOLS], "CNY"),
            ("stock_hk_spot_em", "HK", [s for s in symbols if s in HK_STOCK_SYMBOLS], "HKD"),
            ("fund_etf_spot_em", "ETF", [s for s in symbols if s in ETF_SYMBOLS], "CNY"),
        ]

        prices: dict[str, RawPrice] = {}
        for function_name, category, group_symbols, currency in groups:
            prices.update(
                self._fetch_group(
                    fetch_fn=getattr(ak, function_name),
                    symbols=group_symbols,
                    currency=currency,
                    fetch_time=fetch_time,
                    function_name=function_name,
                    category=category,
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
                )
        return prices

    def _fetch_group(
        self,
        fetch_fn: Any,
        symbols: list[str],
        currency: str,
        fetch_time: datetime,
        function_name: str,
        category: str,
    ) -> dict[str, RawPrice]:
        if not symbols:
            return {}
        try:
            df = fetch_fn()
        except Exception as exc:
            return {
                symbol: _error_price(
                    symbol=symbol,
                    fetch_time=fetch_time,
                    quality_issues=["provider_error"],
                    currency=currency,
                    function_name=function_name,
                    category=category,
                    exception=exc,
                )
                for symbol in symbols
            }

        matched_symbols = [symbol for symbol in symbols if _find_row(symbol, df) is not None]
        diagnostics = {
            "provider": "akshare",
            "function_name": function_name,
            "category": category,
            "status": "success",
            "returned_rows": 0 if df is None else len(df),
            "matched_symbols": matched_symbols,
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
            "quote_time_raw": quote_raw or "",
            "quote_time_utc": quote_time.astimezone(timezone.utc).isoformat() if quote_time else "",
            "fetch_time_utc": fetch_time.isoformat(),
        }

        return RawPrice(
            symbol=symbol,
            name=_extract_text(row, ["名称", "股票简称", "基金简称", "简称"]) or symbol,
            market=_market_for_symbol(symbol),
            price=price,
            currency=currency,
            source="akshare",
            quote_time=quote_time,
            fetch_time=fetch_time,
            market_status="open",
            quality_issues=issues,
            provider_diagnostics=row_diagnostics,
        )


def _import_akshare() -> Any:
    try:
        import akshare as ak
    except ImportError as exc:
        raise ImportError("akshare_not_installed") from exc
    return ak


def _find_row(symbol: str, df: pd.DataFrame) -> pd.Series | None:
    if df is None or df.empty:
        return None
    target_codes = _candidate_codes(symbol)
    code_columns = ["代码", "证券代码", "股票代码", "基金代码", "symbol", "代码代码"]
    for column in code_columns:
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
    for column in ["最新价", "最新", "现价", "收盘", "价格"]:
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
    for column in ["更新时间", "update_time", "quote_time", "时间", "数据时间", "数据日期"]:
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
) -> RawPrice:
    provider_diagnostics = {
        "provider": "akshare",
        "function_name": function_name,
        "symbol": symbol,
        "category": category,
        "status": "fail" if "provider_error" in quality_issues or "akshare_not_installed" in quality_issues else "success",
        "fetch_time_utc": fetch_time.isoformat(),
    }
    if diagnostics:
        provider_diagnostics.update(diagnostics)
        provider_diagnostics["symbol"] = symbol
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
