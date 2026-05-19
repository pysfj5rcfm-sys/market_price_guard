from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .models import PriceRecord


ETF_SYMBOLS = {"159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"}
RECONCILIATION_SYMBOLS = ETF_SYMBOLS | {"601899.SH", "601985.SH", "003816.SZ"}
REAL_SOURCES = {"eastmoney_direct", "akshare", "yfinance"}
BLOCKING_ISSUES = {
    "provider_error",
    "akshare_not_installed",
    "yfinance_not_installed",
    "symbol_not_found",
    "invalid_price",
    "invalid_quote_time",
    "quote_time_missing",
    "provider_timeout",
}
ETF_THRESHOLDS = (0.15, 0.30, 0.80)
A_SHARE_THRESHOLDS = (0.20, 0.50, 1.00)


@dataclass(frozen=True)
class SourceQuote:
    source: str
    price: float | None
    quote_time: datetime | None
    status: str = "success"
    issues: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return self.source in REAL_SOURCES and self.price is not None and self.quote_time is not None and not (set(self.issues) & BLOCKING_ISSUES)


def apply_reconciliation(records: list[PriceRecord]) -> list[PriceRecord]:
    for record in records:
        result = reconcile_record(record)
        for key, value in result.items():
            setattr(record, key, value)
        record.provider_diagnostics = {
            **record.provider_diagnostics,
            "reconciliation_enabled": record.reconciliation_enabled,
            "source_agreement_status": record.source_agreement_status,
            "compared_sources": record.compared_sources,
            "reference_source": record.reference_source,
            "candidate_source": record.candidate_source,
            "price_diff_abs": record.price_diff_abs if record.price_diff_abs is not None else "",
            "price_diff_pct": record.price_diff_pct if record.price_diff_pct is not None else "",
            "quote_time_gap_seconds": record.quote_time_gap_seconds if record.quote_time_gap_seconds is not None else "",
            "operation_candidate_agreed": record.operation_candidate_agreed,
            "reconciliation_note": record.reconciliation_note,
        }
    return records


def reconcile_record(record: PriceRecord) -> dict[str, object]:
    if record.symbol not in RECONCILIATION_SYMBOLS:
        return _empty_result("not_in_reconciliation_scope")
    quotes = _quotes_for_record(record)
    valid = [quote for quote in quotes if quote.valid]
    errors = [quote for quote in quotes if quote.source in REAL_SOURCES and not quote.valid and quote.issues]
    if not valid:
        status = "provider_error" if errors else "insufficient_data"
        return {
            **_empty_result("no comparable real provider quotes"),
            "reconciliation_enabled": True,
            "source_agreement_status": status,
            "compared_sources": _join_sources([quote.source for quote in quotes if quote.source in REAL_SOURCES]),
        }
    if len(valid) == 1:
        return {
            **_empty_result("only one valid real provider quote"),
            "reconciliation_enabled": True,
            "source_agreement_status": "single_source_only",
            "compared_sources": valid[0].source,
            "reference_source": valid[0].source,
        }

    reference = _preferred_reference(valid, record)
    max_abs = 0.0
    max_pct = 0.0
    candidate = ""
    for quote in valid:
        if quote.source == reference.source:
            continue
        diff_abs = abs(float(quote.price or 0) - float(reference.price or 0))
        diff_pct = (diff_abs / float(reference.price or 1)) * 100 if reference.price else 0.0
        if diff_pct >= max_pct:
            max_abs = diff_abs
            max_pct = diff_pct
            candidate = quote.source
    gap = _max_quote_time_gap_seconds(valid)
    status = _agreement_status(record.symbol, max_pct)
    time_note = _time_gap_note(gap)
    return {
        "reconciliation_enabled": True,
        "source_agreement_status": status,
        "compared_sources": _join_sources([quote.source for quote in valid]),
        "reference_source": reference.source,
        "candidate_source": candidate,
        "price_diff_abs": round(max_abs, 6),
        "price_diff_pct": round(max_pct, 6),
        "quote_time_gap_seconds": gap,
        "reconciliation_note": f"{status}; {time_note}; diagnostic only; does not upgrade reference-grade to operation-grade",
        "operation_candidate_agreed": status == "aligned",
    }


def build_reconciliation_report(records: list[PriceRecord], runtime: dict[str, Any] | None = None) -> str:
    runtime = runtime or {}
    summary = reconciliation_summary(records)
    lines = [
        "# market_price_guard 多源价格差异检查报告",
        "",
        "## 基本信息",
        f"- generated_at: {runtime.get('run_end_time_utc', '')}",
        f"- profile: {runtime.get('profile', '')}",
        f"- provider_mode: {runtime.get('provider_mode', '')}",
        f"- provider_policy: {runtime.get('provider_policy', '')}",
        f"- quote_purpose: {runtime.get('quote_purpose', 'operation')}",
        "- reconciliation_enabled: true",
        "",
        "## 总结",
    ]
    for key in [
        "total_symbols",
        "reconciled_symbols",
        "single_source_only",
        "aligned",
        "minor_diff",
        "warning_diff",
        "major_diff",
        "insufficient_data",
        "provider_error",
    ]:
        lines.append(f"- {key}: {summary.get(key, 0)}")
    lines.extend(
        [
            "",
            "## 每个 symbol 的比较表",
            "| symbol | name | asset_role | compared_sources | selected_provider | reference_source | candidate_sources | prices_by_source | quote_times_by_source | max_price_diff_abs | max_price_diff_pct | max_quote_time_gap_seconds | source_agreement_status | operation_candidate_agreed | reconciliation_note |",
            "|---|---|---|---|---|---|---|---|---|---:|---:|---:|---|---|---|",
        ]
    )
    for record in records:
        if not record.reconciliation_enabled:
            continue
        quotes = _quotes_for_record(record)
        lines.append(
            "| {symbol} | {name} | {asset_role} | {sources} | {selected} | {reference} | {candidate} | {prices} | {times} | {diff_abs} | {diff_pct} | {gap} | {status} | {agreed} | {note} |".format(
                symbol=record.symbol,
                name=record.name,
                asset_role=record.asset_role or "",
                sources=record.compared_sources,
                selected=record.selected_provider or record.source,
                reference=record.reference_source,
                candidate=record.candidate_source,
                prices=_prices_by_source(quotes),
                times=_quote_times_by_source(quotes),
                diff_abs="" if record.price_diff_abs is None else record.price_diff_abs,
                diff_pct="" if record.price_diff_pct is None else record.price_diff_pct,
                gap="" if record.quote_time_gap_seconds is None else record.quote_time_gap_seconds,
                status=record.source_agreement_status,
                agreed=record.operation_candidate_agreed,
                note=record.reconciliation_note,
            )
        )
    if not any(record.reconciliation_enabled for record in records):
        lines.append("|  |  |  |  |  |  |  |  |  |  |  |  | insufficient_data | False | no symbols in reconciliation scope |")
    lines.extend(
        [
            "",
            "## 使用边界",
            "- Multi-source reconciliation is for data quality diagnostics only.",
            "- It does not provide trading advice.",
            "- It does not automatically upgrade reference-grade data to operation-grade.",
            "- Operation analysis still requires strict, freshness, quote_trust_tier, and usable_for_operation checks to pass.",
        ]
    )
    return "\n".join(lines) + "\n"


def reconciliation_summary(records: list[PriceRecord]) -> dict[str, int]:
    keys = {
        "total_symbols": 0,
        "reconciled_symbols": 0,
        "single_source_only": 0,
        "aligned": 0,
        "minor_diff": 0,
        "warning_diff": 0,
        "major_diff": 0,
        "insufficient_data": 0,
        "provider_error": 0,
    }
    scoped = [record for record in records if record.reconciliation_enabled]
    keys["total_symbols"] = len(scoped)
    for record in scoped:
        status = record.source_agreement_status or "insufficient_data"
        if status in keys:
            keys[status] += 1
        if status in {"aligned", "minor_diff", "warning_diff", "major_diff"}:
            keys["reconciled_symbols"] += 1
    return keys


def _quotes_for_record(record: PriceRecord) -> list[SourceQuote]:
    quotes: list[SourceQuote] = []
    selected_source = record.selected_provider or record.source
    if selected_source in REAL_SOURCES:
        quotes.append(
            SourceQuote(
                source=selected_source,
                price=record.price,
                quote_time=record.quote_time,
                status="success" if record.price is not None and record.quote_time is not None else "failed",
                issues=tuple(record.quality_issues),
            )
        )
    for item in record.provider_diagnostics.get("reconciliation_sources", []) or []:
        if not isinstance(item, dict):
            continue
        quotes.append(
            SourceQuote(
                source=str(item.get("source") or item.get("provider") or ""),
                price=_float_or_none(item.get("price")),
                quote_time=_datetime_or_none(item.get("quote_time")),
                status=str(item.get("status", "")),
                issues=tuple(str(issue) for issue in item.get("quality_issues", []) or []),
            )
        )
    deduped: dict[str, SourceQuote] = {}
    for quote in quotes:
        if quote.source in REAL_SOURCES and quote.source not in deduped:
            deduped[quote.source] = quote
    return list(deduped.values())


def _preferred_reference(valid: list[SourceQuote], record: PriceRecord) -> SourceQuote:
    selected = record.selected_provider or record.source
    for quote in valid:
        if quote.source == selected:
            return quote
    return valid[0]


def _agreement_status(symbol: str, diff_pct: float) -> str:
    aligned, minor, warning = ETF_THRESHOLDS if symbol in ETF_SYMBOLS else A_SHARE_THRESHOLDS
    if diff_pct <= aligned:
        return "aligned"
    if diff_pct <= minor:
        return "minor_diff"
    if diff_pct <= warning:
        return "warning_diff"
    return "major_diff"


def _max_quote_time_gap_seconds(quotes: list[SourceQuote]) -> float:
    times = [quote.quote_time.astimezone(timezone.utc) for quote in quotes if quote.quote_time is not None]
    if len(times) < 2:
        return 0.0
    return float(round((max(times) - min(times)).total_seconds(), 3))


def _time_gap_note(gap_seconds: float) -> str:
    if gap_seconds <= 300:
        return "time_aligned"
    if gap_seconds <= 1800:
        return "time_gap_warning"
    return "time_gap_large"


def _empty_result(note: str) -> dict[str, object]:
    return {
        "reconciliation_enabled": False,
        "source_agreement_status": "",
        "compared_sources": "",
        "reference_source": "",
        "candidate_source": "",
        "price_diff_abs": None,
        "price_diff_pct": None,
        "quote_time_gap_seconds": None,
        "reconciliation_note": note,
        "operation_candidate_agreed": False,
    }


def _join_sources(sources: list[str]) -> str:
    return ", ".join(dict.fromkeys(source for source in sources if source))


def _float_or_none(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _datetime_or_none(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _prices_by_source(quotes: list[SourceQuote]) -> str:
    return "; ".join(f"{quote.source}={'' if quote.price is None else quote.price}" for quote in quotes)


def _quote_times_by_source(quotes: list[SourceQuote]) -> str:
    return "; ".join(f"{quote.source}={quote.quote_time.isoformat() if quote.quote_time else ''}" for quote in quotes)
