from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from .models import PriceRecord


TIME_COLUMNS = ["时间", "日期时间", "datetime", "time", "timestamp"]
OPEN_COLUMNS = ["开盘", "open"]
HIGH_COLUMNS = ["最高", "high"]
LOW_COLUMNS = ["最低", "low"]
CLOSE_COLUMNS = ["收盘", "close"]
VOLUME_COLUMNS = ["成交量", "volume"]
AMOUNT_COLUMNS = ["成交额", "amount"]


@dataclass(frozen=True)
class MinuteBar:
    timestamp: datetime
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None = None
    amount: float | None = None


@dataclass(frozen=True)
class MinuteBarsSnapshot:
    symbol: str
    provider: str
    interval: str
    bars: list[MinuteBar]
    latest_time: datetime | None
    fetch_time: datetime
    status: str
    validation_status: str
    missing_reason: str
    notes: str = ""


def apply_minute_bars_probe(
    records: list[PriceRecord],
    include_minute_bars: bool = False,
    provider_mode: str = "mock",
) -> tuple[list[PriceRecord], list[dict[str, Any]]]:
    """Attach minute-bar probe status without changing price usability semantics."""
    rows: list[dict[str, Any]] = []
    updated: list[PriceRecord] = []
    for record in records:
        snapshot = _snapshot_for_record(record, include_minute_bars, provider_mode)
        updated_record = _record_with_snapshot(record, snapshot)
        updated.append(updated_record)
        rows.extend(_snapshot_rows(updated_record, snapshot))
    return updated, rows


def _snapshot_for_record(record: PriceRecord, include_minute_bars: bool, provider_mode: str) -> MinuteBarsSnapshot:
    fetch_time = datetime.now(timezone.utc)
    if not include_minute_bars:
        return MinuteBarsSnapshot(
            symbol=record.symbol,
            provider="missing",
            interval="not_available",
            bars=[],
            latest_time=None,
            fetch_time=fetch_time,
            status="not_attempted",
            validation_status="missing",
            missing_reason="not_attempted",
            notes="minute probe not enabled",
        )

    if record.source == "manual" or record.symbol == "GOLD_CNY":
        return MinuteBarsSnapshot(
            symbol=record.symbol,
            provider="manual",
            interval="not_available",
            bars=[],
            latest_time=None,
            fetch_time=fetch_time,
            status="not_supported",
            validation_status="not_supported",
            missing_reason="manual_price_only",
            notes="manual price only; minute bars are not supported",
        )

    if "symbol_not_found" in record.quality_issues:
        return MinuteBarsSnapshot(
            symbol=record.symbol,
            provider=record.selected_provider or record.source or "missing",
            interval="not_available",
            bars=[],
            latest_time=None,
            fetch_time=fetch_time,
            status="symbol_not_found",
            validation_status="missing",
            missing_reason="symbol_not_found",
            notes="provider did not return this symbol",
        )

    if "provider_error" in record.quality_issues:
        return MinuteBarsSnapshot(
            symbol=record.symbol,
            provider=record.selected_provider or record.source or "missing",
            interval="not_available",
            bars=[],
            latest_time=None,
            fetch_time=fetch_time,
            status="provider_error",
            validation_status="missing",
            missing_reason="provider_error",
            notes="price provider error; minute probe skipped",
        )

    if provider_mode == "mock" and record.price is not None:
        return _mock_snapshot(record, fetch_time)

    if _is_etf_symbol(record.symbol):
        return _akshare_etf_snapshot(record, fetch_time)

    provider = record.selected_provider or record.source or "missing"
    validation = "not_validated" if provider in {"eastmoney_direct", "yfinance"} else "not_supported"
    return MinuteBarsSnapshot(
        symbol=record.symbol,
        provider=provider,
        interval="not_available",
        bars=[],
        latest_time=None,
        fetch_time=fetch_time,
        status="not_supported",
        validation_status=validation,
        missing_reason="not_implemented_for_provider",
        notes=f"minute bars probe is not implemented for {provider} in v0.7.2a.1",
    )


def _mock_snapshot(record: PriceRecord, fetch_time: datetime) -> MinuteBarsSnapshot:
    latest = record.quote_time.astimezone(timezone.utc) if record.quote_time else fetch_time
    price = float(record.price or 0)
    bars = [
        MinuteBar(timestamp=latest - timedelta(minutes=1), open=price, high=price, low=price, close=price),
        MinuteBar(timestamp=latest, open=price, high=price, low=price, close=price),
    ]
    return MinuteBarsSnapshot(
        symbol=record.symbol,
        provider="mock",
        interval="1m",
        bars=bars,
        latest_time=latest,
        fetch_time=fetch_time,
        status="available",
        validation_status="development_only",
        missing_reason="",
        notes="mock minute bars for tests only",
    )


def _record_with_snapshot(record: PriceRecord, snapshot: MinuteBarsSnapshot) -> PriceRecord:
    return record.model_copy(
        update={
            "minute_bars_available": snapshot.status == "available" and bool(snapshot.bars),
            "minute_bar_provider": snapshot.provider,
            "minute_bar_interval": snapshot.interval,
            "minute_bar_count": len(snapshot.bars),
            "minute_bar_latest_time": snapshot.latest_time.isoformat() if snapshot.latest_time else "",
            "minute_bar_fetch_time": snapshot.fetch_time.isoformat(),
            "minute_bar_status": snapshot.status,
            "minute_bar_validation_status": snapshot.validation_status,
            "minute_bar_missing_reason": snapshot.missing_reason,
            "minute_bar_notes": snapshot.notes,
        }
    )


def _snapshot_rows(record: PriceRecord, snapshot: MinuteBarsSnapshot) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bar in snapshot.bars:
        rows.append(
            {
                "symbol": record.symbol,
                "name": record.name,
                "provider": snapshot.provider,
                "interval": snapshot.interval,
                "timestamp": bar.timestamp.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "amount": bar.amount,
                "validation_status": snapshot.validation_status,
                "notes": snapshot.notes,
            }
        )
    return rows


def _akshare_etf_snapshot(record: PriceRecord, fetch_time: datetime) -> MinuteBarsSnapshot:
    try:
        ak = _import_akshare()
    except ImportError as exc:
        return MinuteBarsSnapshot(
            symbol=record.symbol,
            provider="akshare",
            interval="not_available",
            bars=[],
            latest_time=None,
            fetch_time=fetch_time,
            status="provider_error",
            validation_status="missing",
            missing_reason="provider_error",
            notes=f"akshare import failed: {exc}",
        )

    normalized = _normalize_symbol(record.symbol)
    last_error = ""
    for period in ["1", "5"]:
        interval = f"{period}m"
        try:
            df = _call_akshare_minute_bars(ak, normalized, period)
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {str(exc)[:160]}"
            continue
        if df is None or df.empty:
            last_error = "empty_response"
            continue
        bars, validation_status = _minute_bars_from_df(df)
        if not bars:
            last_error = "no_parseable_bars"
            continue
        latest = max(bar.timestamp for bar in bars)
        return MinuteBarsSnapshot(
            symbol=record.symbol,
            provider="akshare",
            interval=interval,
            bars=bars,
            latest_time=latest,
            fetch_time=fetch_time,
            status="available",
            validation_status=validation_status,
            missing_reason="",
            notes=f"fund_etf_hist_min_em normalized_symbol={normalized}",
        )

    status = "unavailable" if last_error in {"empty_response", "no_parseable_bars"} else "provider_error"
    reason = "empty_response" if last_error == "empty_response" else ("no_recent_bars" if last_error == "no_parseable_bars" else "provider_error")
    return MinuteBarsSnapshot(
        symbol=record.symbol,
        provider="akshare",
        interval="not_available",
        bars=[],
        latest_time=None,
        fetch_time=fetch_time,
        status=status,
        validation_status="not_validated",
        missing_reason=reason,
        notes=f"fund_etf_hist_min_em normalized_symbol={normalized}; {last_error or 'unknown'}",
    )


def _call_akshare_minute_bars(ak: Any, symbol: str, period: str) -> pd.DataFrame:
    fetch_fn = getattr(ak, "fund_etf_hist_min_em")
    try:
        return fetch_fn(symbol=symbol, period=period, adjust="")
    except TypeError:
        return fetch_fn(symbol=symbol, period=period)


def _minute_bars_from_df(df: pd.DataFrame) -> tuple[list[MinuteBar], str]:
    bars: list[MinuteBar] = []
    validation_status = "provider_raw"
    for _idx, row in df.iterrows():
        timestamp_raw = _value(row, TIME_COLUMNS)
        timestamp = _parse_timestamp(timestamp_raw)
        if timestamp is None:
            validation_status = "provider_dependent"
            continue
        close = _to_float(_value(row, CLOSE_COLUMNS))
        bars.append(
            MinuteBar(
                timestamp=timestamp,
                open=_to_float(_value(row, OPEN_COLUMNS)),
                high=_to_float(_value(row, HIGH_COLUMNS)),
                low=_to_float(_value(row, LOW_COLUMNS)),
                close=close,
                volume=_to_float(_value(row, VOLUME_COLUMNS)),
                amount=_to_float(_value(row, AMOUNT_COLUMNS)),
            )
        )
    return bars, validation_status


def _value(row: pd.Series, candidates: list[str]) -> Any:
    lookup = {_normalize_column(column): column for column in row.index}
    for candidate in candidates:
        column = candidate if candidate in row else lookup.get(_normalize_column(candidate))
        if column is not None:
            return row[column]
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().replace("/", "-")
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone(timedelta(hours=8)))
    return parsed


def _to_float(value: Any) -> float | None:
    if value is None or pd.isna(value) or value == "":
        return None
    try:
        return float(str(value).replace("%", ""))
    except (TypeError, ValueError):
        return None


def _normalize_column(value: Any) -> str:
    return str(value).strip().lower()


def _normalize_symbol(symbol: str) -> str:
    return symbol.split(".")[0]


def _is_etf_symbol(symbol: str) -> bool:
    if not symbol.endswith((".SH", ".SZ")):
        return False
    return symbol.split(".")[0].startswith(("15", "51", "52", "56", "58"))


def _import_akshare() -> Any:
    try:
        import akshare as ak
    except ImportError as exc:
        raise ImportError("akshare_not_installed") from exc
    return ak
