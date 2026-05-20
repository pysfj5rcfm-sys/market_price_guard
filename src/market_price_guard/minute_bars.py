from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .models import PriceRecord


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
        notes=f"minute bars probe is not implemented for {provider} in v0.7.2a",
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
                "provider": snapshot.provider,
                "interval": snapshot.interval,
                "timestamp": bar.timestamp.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "amount": bar.amount,
            }
        )
    return rows
