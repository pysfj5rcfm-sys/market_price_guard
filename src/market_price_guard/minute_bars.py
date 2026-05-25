from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from .models import PriceRecord
from .providers.eastmoney_direct_provider import _default_http_get, eastmoney_secid_for_symbol
from .providers.yfinance_provider import yahoo_ticker_for_symbol
from .yfinance_circuit import YFinanceCircuitBreaker


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
    market_session: str = ""
    after_close_possible: bool = False
    retry_suggested: str = ""
    retry_reason: str = ""
    after_close_applies_to: str = ""
    upload_note: str = ""
    yfinance_ticker: str = ""


def apply_minute_bars_probe(
    records: list[PriceRecord],
    include_minute_bars: bool = False,
    provider_mode: str = "mock",
    now: datetime | None = None,
    minute_mode: str = "diagnostic",
    minute_workers: int = 0,
    yfinance_circuit: YFinanceCircuitBreaker | None = None,
) -> tuple[list[PriceRecord], list[dict[str, Any]]]:
    """Attach minute-bar probe status without changing price usability semantics."""
    rows: list[dict[str, Any]] = []
    updated: list[PriceRecord] = []
    for record in records:
        start = datetime.now(timezone.utc)
        snapshot = _snapshot_for_record(record, include_minute_bars, provider_mode, now, minute_mode, yfinance_circuit)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        updated_record = _record_with_snapshot(record, snapshot, minute_mode, minute_workers, elapsed)
        updated.append(updated_record)
        rows.extend(_snapshot_rows(updated_record, snapshot))
    return updated, rows


def _snapshot_for_record(
    record: PriceRecord,
    include_minute_bars: bool,
    provider_mode: str,
    now: datetime | None = None,
    minute_mode: str = "diagnostic",
    yfinance_circuit: YFinanceCircuitBreaker | None = None,
) -> MinuteBarsSnapshot:
    fetch_time = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
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
        upload_note="minute_probe_not_enabled",
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
            upload_note="manual_price_only; minute_not_supported",
        )

    if provider_mode == "mock" and record.price is not None:
        return _mock_snapshot(record, fetch_time)

    if _is_etf_symbol(record.symbol):
        return _etf_snapshot_with_fallback(record, fetch_time, minute_mode, yfinance_circuit)

    if _is_cn_security(record.symbol):
        eastmoney_snapshot = None
        if minute_mode == "diagnostic":
            eastmoney_snapshot = _eastmoney_snapshot(record, fetch_time, previous_note="akshare_not_applicable_for_stock_minute_probe")
            if eastmoney_snapshot.status == "available":
                return eastmoney_snapshot
        return _yfinance_snapshot_with_circuit(
            record,
            fetch_time,
            previous_note=_eastmoney_attempt_note(eastmoney_snapshot) if eastmoney_snapshot else "eastmoney_status=skipped; eastmoney_reason=fallback_skipped_balanced_mode",
            previous_snapshot=eastmoney_snapshot,
            attempted_providers="eastmoney_direct,yfinance" if eastmoney_snapshot else "yfinance",
            circuit=yfinance_circuit,
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
        notes=f"minute bars are not supported for {provider} in current reference-only probe path",
    )


def _etf_snapshot_with_fallback(
    record: PriceRecord,
    fetch_time: datetime,
    minute_mode: str,
    yfinance_circuit: YFinanceCircuitBreaker | None = None,
) -> MinuteBarsSnapshot:
    akshare_snapshot = _akshare_etf_snapshot(record, fetch_time)
    if akshare_snapshot.status == "available":
        return akshare_snapshot
    if minute_mode == "fast":
        return _snapshot_with_notes(
            akshare_snapshot,
            extra_note="provider_attempted=akshare; provider_success=none; fallback_skipped_fast_mode=true; retry_with_balanced_or_diagnostic",
            upload_note="akshare_failed; fallback_skipped_fast_mode; retry_balanced_or_diagnostic",
        )
    if minute_mode == "balanced":
        return _yfinance_snapshot_with_circuit(
            record,
            fetch_time,
            previous_note=f"{_snapshot_attempt_note(akshare_snapshot)}; eastmoney_status=skipped; eastmoney_reason=fallback_skipped_balanced_mode",
            previous_snapshot=akshare_snapshot,
            attempted_providers="akshare,yfinance",
            circuit=yfinance_circuit,
        )
    eastmoney_snapshot = _eastmoney_snapshot(
        record,
        fetch_time,
        previous_note=_snapshot_attempt_note(akshare_snapshot),
        previous_snapshot=akshare_snapshot,
    )
    if eastmoney_snapshot.status == "available":
        return eastmoney_snapshot
    return _yfinance_snapshot_with_circuit(
        record,
        fetch_time,
        previous_note=_eastmoney_attempt_note(eastmoney_snapshot),
        previous_snapshot=eastmoney_snapshot,
        attempted_providers="akshare,eastmoney_direct,yfinance",
        circuit=yfinance_circuit,
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


def _record_with_snapshot(
    record: PriceRecord,
    snapshot: MinuteBarsSnapshot,
    minute_mode: str = "",
    minute_workers: int = 0,
    elapsed_seconds: float | None = None,
) -> PriceRecord:
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
            "minute_bar_market_session": snapshot.market_session,
            "minute_bar_after_close_possible": snapshot.after_close_possible,
            "minute_bar_retry_suggested": snapshot.retry_suggested,
            "minute_bar_retry_reason": snapshot.retry_reason,
            "minute_bar_after_close_applies_to": snapshot.after_close_applies_to,
            "minute_bar_upload_note": snapshot.upload_note or _minute_bar_upload_note(snapshot),
            "yfinance_ticker": snapshot.yfinance_ticker,
            "minute_mode": minute_mode,
            "minute_workers": minute_workers,
            "parallel_enabled": False,
            "parallel_note": "workers parameter parsed, execution remains serial in this version",
            "per_symbol_elapsed_seconds": round(elapsed_seconds, 3) if elapsed_seconds is not None else None,
            "fallback_skipped_fast_mode": record.fallback_skipped_fast_mode or "fallback_skipped_fast_mode=true" in snapshot.notes,
            "base_quote_provider_attempted": record.base_quote_provider_attempted or record.provider_attempted,
            "minute_provider_attempted": _provider_attempted_from_notes(snapshot.notes) or snapshot.provider or "missing",
            "provider_attempted": record.base_quote_provider_attempted or record.provider_attempted,
            "yfinance_fallback_policy": _minute_yfinance_fallback_policy(minute_mode),
            "yfinance_circuit_open": "yfinance_circuit_open=true" in snapshot.notes,
            "yfinance_circuit_reason": _note_value(snapshot.notes, "yfinance_circuit_reason"),
            "fallback_skipped_yfinance_circuit_open": "fallback_skipped_yfinance_circuit_open" in snapshot.notes,
            "provider_success": snapshot.status == "available" or record.provider_success,
        }
    )


def _snapshot_rows(record: PriceRecord, snapshot: MinuteBarsSnapshot) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bar in snapshot.bars:
        rows.append(
            {
                "symbol": record.symbol,
                "name": record.name,
                "source_universe": record.source_universe,
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


def _snapshot_with_notes(snapshot: MinuteBarsSnapshot, extra_note: str, upload_note: str) -> MinuteBarsSnapshot:
    return MinuteBarsSnapshot(
        symbol=snapshot.symbol,
        provider=snapshot.provider,
        interval=snapshot.interval,
        bars=snapshot.bars,
        latest_time=snapshot.latest_time,
        fetch_time=snapshot.fetch_time,
        status=snapshot.status,
        validation_status=snapshot.validation_status,
        missing_reason=snapshot.missing_reason,
        notes=f"{snapshot.notes}; {extra_note}" if snapshot.notes else extra_note,
        market_session=snapshot.market_session,
        after_close_possible=snapshot.after_close_possible,
        retry_suggested=snapshot.retry_suggested,
        retry_reason=snapshot.retry_reason,
        after_close_applies_to=snapshot.after_close_applies_to,
        upload_note=upload_note,
        yfinance_ticker=snapshot.yfinance_ticker,
    )


def _provider_attempted_from_notes(notes: str) -> str:
    marker = "provider_attempted="
    if marker not in notes:
        return ""
    tail = notes.split(marker, 1)[1]
    return tail.split(";", 1)[0].strip()


def _note_value(notes: str, key: str) -> str:
    marker = f"{key}="
    if marker not in notes:
        return ""
    return notes.split(marker, 1)[1].split(";", 1)[0].strip()


def _minute_yfinance_fallback_policy(minute_mode: str) -> str:
    if minute_mode == "fast":
        return "disabled_in_fast_mode"
    if minute_mode == "balanced":
        return "enabled_until_circuit_open"
    if minute_mode == "diagnostic":
        return "enabled_with_circuit_breaker"
    return ""


def _akshare_etf_snapshot(record: PriceRecord, fetch_time: datetime) -> MinuteBarsSnapshot:
    success_diagnostic = _market_session_diagnostic(record, fetch_time, akshare_failed=False)
    try:
        ak = _import_akshare()
    except ImportError as exc:
        diagnostic = _market_session_diagnostic(record, fetch_time, akshare_failed=True)
        error_message = _short_error_message(exc)
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
            notes=(
                f"akshare_error_type={type(exc).__name__}; akshare_error_message={error_message}; "
                f"akshare import failed: {error_message}; {_diagnostic_note(diagnostic)}"
            ),
            **diagnostic,
        )

    normalized = _normalize_symbol(record.symbol)
    last_error = ""
    last_error_type = ""
    last_error_message = ""
    for period in ["1", "5"]:
        interval = f"{period}m"
        try:
            df = _call_akshare_minute_bars(ak, normalized, period)
        except Exception as exc:
            last_error_type = type(exc).__name__
            last_error_message = _short_error_message(exc)
            last_error = f"{last_error_type}: {last_error_message}"
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
            notes=f"provider_attempted=akshare; provider_success=akshare; akshare_status=available; akshare_reason=; akshare_error_type=; akshare_error_message=; fund_etf_hist_min_em normalized_symbol={normalized}; {_diagnostic_note(success_diagnostic)}",
            **success_diagnostic,
        )

    status = "unavailable" if last_error in {"empty_response", "no_parseable_bars"} else "provider_error"
    reason = "empty_response" if last_error == "empty_response" else ("no_recent_bars" if last_error == "no_parseable_bars" else "provider_error")
    diagnostic = _market_session_diagnostic(record, fetch_time, akshare_failed=True)
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
        notes=(
            f"akshare_error_type={last_error_type}; akshare_error_message={_short_text(last_error_message or last_error or 'unknown')}; "
            f"fund_etf_hist_min_em normalized_symbol={normalized}; {last_error or 'unknown'}; {_diagnostic_note(diagnostic)}"
        ),
        **diagnostic,
    )


def _eastmoney_snapshot(
    record: PriceRecord,
    fetch_time: datetime,
    previous_note: str = "",
    previous_snapshot: MinuteBarsSnapshot | None = None,
) -> MinuteBarsSnapshot:
    inherited_diagnostic = _snapshot_diagnostic(previous_snapshot) if previous_snapshot else _market_session_diagnostic(record, fetch_time, akshare_failed=False)
    endpoint = "push2his.eastmoney.com/api/qt/stock/kline/get"
    try:
        secid = eastmoney_secid_for_symbol(record.symbol)
    except ValueError as exc:
        error_message = _short_error_message(exc)
        notes = (
            "provider_attempted=akshare,eastmoney_direct; provider_success=none; "
            "eastmoney_status=symbol_not_found; eastmoney_reason=secid_mapping_failed; "
            f"eastmoney_endpoint={endpoint}; eastmoney_secid=; eastmoney_error_type={type(exc).__name__}; "
            f"eastmoney_error_message={error_message}; {previous_note}; {_diagnostic_note(inherited_diagnostic)}"
        )
        return MinuteBarsSnapshot(
            symbol=record.symbol,
            provider="eastmoney_direct",
            interval="not_available",
            bars=[],
            latest_time=None,
            fetch_time=fetch_time,
            status="symbol_not_found",
            validation_status="missing",
            missing_reason="secid_mapping_failed",
            notes=notes,
            **inherited_diagnostic,
        )

    last_error = ""
    last_reason = "provider_error"
    last_error_type = ""
    last_error_message = ""
    for klt, interval in [("1", "1m"), ("5", "5m")]:
        try:
            payload = _call_eastmoney_minute_bars(secid, klt)
        except Exception as exc:
            last_error_type = type(exc).__name__
            last_error_message = _short_error_message(exc)
            last_error = f"{last_error_type}: {last_error_message}"
            last_reason = "provider_error"
            continue
        bars, reason, raw_count = _eastmoney_bars_from_payload(payload)
        if bars:
            latest = max(bar.timestamp for bar in bars)
            return MinuteBarsSnapshot(
                symbol=record.symbol,
                provider="eastmoney_direct",
                interval=interval,
                bars=bars,
                latest_time=latest,
                fetch_time=fetch_time,
                status="available",
                validation_status="provider_dependent",
                missing_reason="",
                notes=(
                    f"provider_attempted=akshare,eastmoney_direct; provider_success=eastmoney_direct; "
                    f"eastmoney_status=available; eastmoney_reason=; eastmoney_endpoint={endpoint}; "
                    f"eastmoney_secid={secid}; eastmoney_error_type=; eastmoney_error_message=; "
                    f"interval={interval}; raw_count={raw_count}; parsed_count={len(bars)}; "
                    f"{previous_note}; {_diagnostic_note(inherited_diagnostic)}"
                ),
                **inherited_diagnostic,
            )
        last_error = f"{reason}; raw_count={raw_count}"
        last_reason = reason
        last_error_type = ""
        last_error_message = last_error

    status = "unavailable" if last_reason in {"empty_response", "no_recent_bars"} else "provider_error"
    if last_reason == "parse_error":
        status = "parse_error"
    error_type = last_error_type or ("ParseError" if last_reason == "parse_error" else "")
    error_message = last_error_message or _short_text(last_error or "unknown")
    return MinuteBarsSnapshot(
        symbol=record.symbol,
        provider="eastmoney_direct",
        interval="not_available",
        bars=[],
        latest_time=None,
        fetch_time=fetch_time,
        status=status,
        validation_status="not_validated",
        missing_reason=last_reason,
        notes=(
            f"provider_attempted=akshare,eastmoney_direct; provider_success=none; "
            f"eastmoney_status={status}; eastmoney_reason={last_reason}; eastmoney_endpoint={endpoint}; "
            f"eastmoney_secid={secid}; eastmoney_error_type={error_type}; eastmoney_error_message={error_message}; "
            f"{previous_note}; {last_error or 'unknown'}; {_diagnostic_note(inherited_diagnostic)}"
        ),
        **inherited_diagnostic,
    )


def _call_eastmoney_minute_bars(secid: str, klt: str) -> dict[str, Any]:
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        "klt": klt,
        "fqt": "1",
        "end": "20500101",
        "lmt": "240",
    }
    return _default_http_get(url, params, timeout_seconds=5.0)


def _yfinance_snapshot_with_circuit(
    record: PriceRecord,
    fetch_time: datetime,
    previous_note: str = "",
    previous_snapshot: MinuteBarsSnapshot | None = None,
    attempted_providers: str = "akshare,eastmoney_direct,yfinance",
    circuit: YFinanceCircuitBreaker | None = None,
) -> MinuteBarsSnapshot:
    if circuit is not None and not circuit.allow():
        circuit.record_skip(scope="minute")
        inherited_diagnostic = _snapshot_diagnostic(previous_snapshot) if previous_snapshot else _market_session_diagnostic(record, fetch_time, akshare_failed=False)
        notes = (
            f"provider_attempted={attempted_providers}; provider_success=none; "
            "yfinance_status=skipped; yfinance_reason=yfinance_circuit_open; "
            f"yfinance_circuit_open=true; yfinance_circuit_reason={circuit.reason}; "
            "fallback_skipped_yfinance_circuit_open=true; "
            f"{previous_note}; {_diagnostic_note(inherited_diagnostic)}"
        )
        return MinuteBarsSnapshot(
            symbol=record.symbol,
            provider="yfinance",
            interval="not_available",
            bars=[],
            latest_time=None,
            fetch_time=fetch_time,
            status="provider_skipped",
            validation_status="provider_dependent",
            missing_reason="yfinance_circuit_open",
            notes=notes,
            upload_note="yfinance_circuit_open; no_minute_bars; see_debug",
            yfinance_ticker="",
            **inherited_diagnostic,
        )
    snapshot = _yfinance_snapshot(record, fetch_time, previous_note, previous_snapshot, attempted_providers, circuit)
    if circuit is not None and circuit.open and "yfinance_circuit_open=true" not in snapshot.notes:
        snapshot = _snapshot_with_notes(
            snapshot,
            extra_note=f"yfinance_circuit_open=true; yfinance_circuit_reason={circuit.reason}",
            upload_note=snapshot.upload_note or _minute_bar_upload_note(snapshot),
        )
    return snapshot


def _yfinance_snapshot(
    record: PriceRecord,
    fetch_time: datetime,
    previous_note: str = "",
    previous_snapshot: MinuteBarsSnapshot | None = None,
    attempted_providers: str = "akshare,eastmoney_direct,yfinance",
    circuit: YFinanceCircuitBreaker | None = None,
) -> MinuteBarsSnapshot:
    inherited_diagnostic = _snapshot_diagnostic(previous_snapshot) if previous_snapshot else _market_session_diagnostic(record, fetch_time, akshare_failed=False)
    if inherited_diagnostic.get("after_close_possible"):
        inherited_diagnostic["after_close_applies_to"] = "akshare,eastmoney_direct"
    try:
        ticker_symbol = _yfinance_minute_ticker_for_symbol(record.symbol)
    except ValueError as exc:
        error_message = _short_error_message(exc)
        return MinuteBarsSnapshot(
            symbol=record.symbol,
            provider="yfinance",
            interval="not_available",
            bars=[],
            latest_time=None,
            fetch_time=fetch_time,
            status="symbol_not_found",
            validation_status="missing",
            missing_reason="yfinance_ticker_mapping_failed",
            notes=(
                f"provider_attempted={attempted_providers}; provider_success=none; "
                "yfinance_status=symbol_not_found; yfinance_reason=yfinance_ticker_mapping_failed; "
                f"yfinance_ticker=; yfinance_error_type={type(exc).__name__}; yfinance_error_message={error_message}; "
                f"{previous_note}; {_diagnostic_note(inherited_diagnostic)}"
            ),
            yfinance_ticker="",
            **inherited_diagnostic,
        )

    last_error = ""
    last_reason = "provider_error"
    last_error_type = ""
    last_error_message = ""
    for interval, period in [("1m", "1d"), ("5m", "5d")]:
        if circuit is not None and not circuit.allow():
            circuit.record_skip(scope="minute")
            last_error_type = ""
            last_error_message = "yfinance_circuit_open"
            last_error = "yfinance_circuit_open"
            last_reason = "yfinance_circuit_open"
            break
        start = time.perf_counter()
        try:
            df = _call_yfinance_minute_bars(ticker_symbol, period=period, interval=interval)
        except ImportError as exc:
            elapsed = time.perf_counter() - start
            last_error_type = type(exc).__name__
            last_error_message = _short_error_message(exc)
            last_error = f"{last_error_type}: {last_error_message}"
            last_reason = "provider_error"
            if circuit is not None:
                circuit.record_error(last_error_message, elapsed_seconds=elapsed, timeout=False, symbol=record.symbol)
            break
        except Exception as exc:
            elapsed = time.perf_counter() - start
            last_error_type = type(exc).__name__
            last_error_message = _short_error_message(exc)
            last_error = f"{last_error_type}: {last_error_message}"
            last_reason = "provider_error"
            if circuit is not None:
                circuit.record_error(
                    last_error_message,
                    elapsed_seconds=elapsed,
                    timeout=elapsed > 8.0,
                    symbol=record.symbol,
                )
            if _looks_yfinance_rate_limited(last_error):
                break
            continue
        elapsed = time.perf_counter() - start
        if df is None or df.empty:
            last_error_type = ""
            last_error_message = "empty_response"
            last_error = "empty_response"
            last_reason = "empty_response"
            if circuit is not None:
                circuit.record_error(last_error_message, elapsed_seconds=elapsed, timeout=elapsed > 8.0, symbol=record.symbol)
            continue
        bars, reason, raw_count = _yfinance_bars_from_frame(df)
        if bars:
            if circuit is not None:
                circuit.record_success(elapsed)
            latest = max(bar.timestamp for bar in bars)
            return MinuteBarsSnapshot(
                symbol=record.symbol,
                provider="yfinance",
                interval=interval,
                bars=bars,
                latest_time=latest,
                fetch_time=fetch_time,
                status="available",
                validation_status="provider_dependent",
                missing_reason="",
                notes=(
                    f"provider_attempted={attempted_providers}; provider_success=yfinance; "
                    "yfinance_status=available; yfinance_reason=; "
                    f"yfinance_ticker={ticker_symbol}; yfinance_error_type=; yfinance_error_message=; "
                    f"interval={interval}; raw_count={raw_count}; parsed_count={len(bars)}; "
                    "reference_only; provider_dependent; not_operation_grade; yfinance_intraday_limit; "
                    f"{previous_note}; {_diagnostic_note(inherited_diagnostic)}"
                ),
                yfinance_ticker=ticker_symbol,
                **inherited_diagnostic,
            )
        last_error_type = "ParseError" if reason == "parse_error" else ""
        last_error_message = reason
        last_error = f"{reason}; raw_count={raw_count}"
        last_reason = reason
        if circuit is not None:
            circuit.record_error(last_error_message, elapsed_seconds=elapsed, timeout=elapsed > 8.0, symbol=record.symbol)

    status = "unavailable" if last_reason in {"empty_response", "no_recent_bars"} else "provider_error"
    if last_reason == "parse_error":
        status = "parse_error"
    if last_reason == "yfinance_circuit_open":
        status = "provider_skipped"
    return MinuteBarsSnapshot(
        symbol=record.symbol,
        provider="yfinance",
        interval="not_available",
        bars=[],
        latest_time=None,
        fetch_time=fetch_time,
        status=status,
        validation_status="provider_dependent",
        missing_reason=last_reason,
        notes=(
            f"provider_attempted={attempted_providers}; provider_success=none; "
            f"yfinance_status={status}; yfinance_reason={last_reason}; "
            f"yfinance_ticker={ticker_symbol}; yfinance_error_type={last_error_type}; "
            f"yfinance_error_message={_short_text(last_error_message or last_error or 'unknown')}; "
            "reference_only; provider_dependent; not_operation_grade; yfinance_intraday_limit; "
            f"{previous_note}; {last_error or 'unknown'}; {_diagnostic_note(inherited_diagnostic)}"
        ),
        yfinance_ticker=ticker_symbol,
        **inherited_diagnostic,
    )


def _call_yfinance_minute_bars(ticker_symbol: str, period: str, interval: str) -> pd.DataFrame:
    yf = _import_yfinance()
    ticker = yf.Ticker(ticker_symbol)
    return ticker.history(period=period, interval=interval)


def _yfinance_bars_from_frame(df: pd.DataFrame) -> tuple[list[MinuteBar], str, int]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return [], "empty_response", 0
    bars: list[MinuteBar] = []
    parse_errors = 0
    for index, row in df.iterrows():
        timestamp = _parse_timestamp(index)
        if timestamp is None:
            parse_errors += 1
            continue
        close = _to_float(_value(row, ["Close", "close"]))
        if close is None:
            parse_errors += 1
            continue
        bars.append(
            MinuteBar(
                timestamp=timestamp,
                open=_to_float(_value(row, ["Open", "open"])),
                high=_to_float(_value(row, ["High", "high"])),
                low=_to_float(_value(row, ["Low", "low"])),
                close=close,
                volume=_to_float(_value(row, ["Volume", "volume"])),
                amount=None,
            )
        )
    if bars:
        return bars, "", len(df)
    return [], "parse_error" if parse_errors else "no_recent_bars", len(df)


def _import_yfinance() -> Any:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError("yfinance_not_installed") from exc
    return yf


def _yfinance_minute_ticker_for_symbol(symbol: str) -> str:
    try:
        return yahoo_ticker_for_symbol(symbol)
    except ValueError:
        if symbol.endswith(".SH"):
            return f"{symbol.split('.')[0]}.SS"
        if symbol.endswith(".SZ"):
            return symbol
        raise


def _eastmoney_bars_from_payload(payload: dict[str, Any]) -> tuple[list[MinuteBar], str, int]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return [], "empty_response", 0
    klines = data.get("klines")
    if not isinstance(klines, list) or not klines:
        return [], "empty_response", 0
    bars: list[MinuteBar] = []
    parse_errors = 0
    for item in klines:
        bar = _eastmoney_bar_from_item(item)
        if bar is None:
            parse_errors += 1
            continue
        bars.append(bar)
    if bars:
        return bars, "", len(klines)
    return [], "parse_error" if parse_errors else "no_recent_bars", len(klines)


def _eastmoney_bar_from_item(item: Any) -> MinuteBar | None:
    if not isinstance(item, str):
        return None
    parts = item.split(",")
    if len(parts) < 6:
        return None
    timestamp = _parse_timestamp(parts[0])
    if timestamp is None:
        return None
    return MinuteBar(
        timestamp=timestamp,
        open=_to_float(parts[1]),
        close=_to_float(parts[2]),
        high=_to_float(parts[3]),
        low=_to_float(parts[4]),
        volume=_to_float(parts[5]),
        amount=_to_float(parts[6]) if len(parts) > 6 else None,
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


def _snapshot_diagnostic(snapshot: MinuteBarsSnapshot) -> dict[str, Any]:
    return {
        "market_session": snapshot.market_session,
        "after_close_possible": snapshot.after_close_possible,
        "retry_suggested": snapshot.retry_suggested,
        "retry_reason": snapshot.retry_reason,
        "after_close_applies_to": snapshot.after_close_applies_to,
    }


def _market_session_diagnostic(record: PriceRecord, fetch_time: datetime, akshare_failed: bool) -> dict[str, Any]:
    session = _cn_market_session(fetch_time) if _is_cn_security(record.symbol) else "unknown"
    after_close_possible = False
    retry_suggested = ""
    retry_reason = ""
    if akshare_failed:
        if session != "cn_trading_hours":
            after_close_possible = True
            retry_suggested = "rerun_during_cn_trading_hours"
            retry_reason = (
                "AKShare minute endpoint failed outside CN continuous trading hours; "
                "market session may be a contributing factor, not a confirmed root cause."
            )
        else:
            retry_suggested = "retry_or_try_fallback_provider"
            retry_reason = "AKShare minute endpoint failed during CN continuous trading hours; use retry or fallback diagnostics."
    return {
        "market_session": session,
        "after_close_possible": after_close_possible,
        "retry_suggested": retry_suggested,
        "retry_reason": retry_reason,
        "after_close_applies_to": "akshare" if after_close_possible else "",
    }


def _cn_market_session(moment: datetime) -> str:
    shanghai = moment.astimezone(timezone(timedelta(hours=8)))
    if shanghai.weekday() >= 5:
        return "cn_non_trading_day"
    minutes = shanghai.hour * 60 + shanghai.minute
    if 9 * 60 + 30 <= minutes < 11 * 60 + 30:
        return "cn_trading_hours"
    if 11 * 60 + 30 <= minutes < 13 * 60:
        return "cn_lunch_break"
    if 13 * 60 <= minutes < 15 * 60:
        return "cn_trading_hours"
    if minutes < 9 * 60 + 30:
        return "cn_pre_open"
    return "cn_after_close"


def _diagnostic_note(diagnostic: dict[str, Any]) -> str:
    return (
        f"market_session={diagnostic.get('market_session', '')}; "
        f"after_close_possible={str(bool(diagnostic.get('after_close_possible'))).lower()}; "
        f"after_close_applies_to={diagnostic.get('after_close_applies_to', '')}; "
        f"retry_suggested={diagnostic.get('retry_suggested', '')}; "
        f"retry_reason={_short_text(str(diagnostic.get('retry_reason', '')))}"
    )


def _short_error_message(exc: Exception) -> str:
    return _short_text(str(exc) or type(exc).__name__)


def _short_text(text: str, limit: int = 160) -> str:
    return text.replace("\n", " ").replace("\r", " ").replace(";", ",")[:limit]


def _looks_yfinance_rate_limited(text: str) -> bool:
    lowered = text.lower()
    return "too many requests" in lowered or "rate limited" in lowered or "yfratelimiterror" in lowered


def _minute_bar_upload_note(snapshot: MinuteBarsSnapshot) -> str:
    if snapshot.provider == "manual" and snapshot.missing_reason == "manual_price_only":
        return "manual_price_only; minute_not_supported"
    if snapshot.status == "available":
        interval = snapshot.interval or "minute"
        if snapshot.provider == "akshare":
            return f"akshare_{interval}_ok; balanced_mode; reference_only"
        if snapshot.provider == "eastmoney_direct":
            return f"eastmoney_{interval}_ok; diagnostic_mode; reference_only; not_operation_grade"
        if snapshot.provider == "yfinance":
            if snapshot.after_close_possible:
                return "yf_ref_ok; ak/em after_close_possible; provider_dependent; not_operation_grade"
            return "yf_ref_ok; provider_dependent; not_operation_grade"
        return f"{snapshot.provider}_minute_ok; reference_only"
    if snapshot.status == "not_supported" and snapshot.missing_reason == "manual_price_only":
        return "manual_price_only; minute_not_supported"
    if snapshot.status == "not_attempted":
        return "minute_probe_not_enabled"
    if "yfinance" in snapshot.notes and "provider_attempted=akshare,eastmoney_direct,yfinance" in snapshot.notes:
        return "all_minute_providers_failed; see_debug"
    return f"{snapshot.status or 'minute_unavailable'}; see_debug"


def _snapshot_attempt_note(snapshot: MinuteBarsSnapshot) -> str:
    return (
        f"akshare_status={snapshot.status}; akshare_reason={snapshot.missing_reason}; "
        f"akshare_note={snapshot.notes}"
    )


def _eastmoney_attempt_note(snapshot: MinuteBarsSnapshot) -> str:
    return (
        f"eastmoney_status={snapshot.status}; eastmoney_reason={snapshot.missing_reason}; "
        f"eastmoney_note={snapshot.notes}"
    )


def _is_cn_security(symbol: str) -> bool:
    return symbol.endswith((".SH", ".SZ"))


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
