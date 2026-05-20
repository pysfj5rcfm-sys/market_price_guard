from __future__ import annotations

from .models import PriceRecord


RANKING_UNIVERSES = {"candidate_watchlist", "scan_universe"}


def apply_scan_ranking(records: list[PriceRecord]) -> list[PriceRecord]:
    for record in records:
        if record.universe_type not in RANKING_UNIVERSES:
            continue
        result = rank_record(record)
        for key, value in result.items():
            setattr(record, key, value)
        record.provider_diagnostics = {
            **record.provider_diagnostics,
            **result,
        }
    return records


def rank_record(record: PriceRecord) -> dict[str, object]:
    exclusion = _rank_exclusion_reason(record)
    if exclusion != "none":
        return {
            "rankable": False,
            "rank_exclusion_reason": exclusion,
            "scan_status": _not_rankable_status(exclusion),
            "watch_priority": "not_rankable",
            "scan_score_basic": None,
            "data_quality_score": None,
            "momentum_score_basic": None,
            "field_reliability_score": None,
            "liquidity_score_basic": None,
            "reconciliation_score": None,
            "scan_score_notes": _notes(record, exclusion),
        }

    data_quality = _data_quality_score(record)
    momentum = _momentum_score(record.price_change_pct)
    field_reliability = _field_reliability_score(record.field_validation_status)
    liquidity = _liquidity_score(record)
    reconciliation = _reconciliation_score(record.source_agreement_status)
    score = round(
        data_quality * 0.35
        + momentum * 0.25
        + field_reliability * 0.20
        + liquidity * 0.10
        + reconciliation * 0.10,
        2,
    )
    priority = _watch_priority(score, record)
    return {
        "rankable": True,
        "rank_exclusion_reason": "none",
        "scan_status": "review_candidate" if priority in {"high", "medium"} else "reference_candidate",
        "watch_priority": priority,
        "scan_score_basic": score,
        "data_quality_score": data_quality,
        "momentum_score_basic": momentum,
        "field_reliability_score": field_reliability,
        "liquidity_score_basic": liquidity,
        "reconciliation_score": reconciliation,
        "scan_score_notes": _notes(record, "none"),
    }


def _rank_exclusion_reason(record: PriceRecord) -> str:
    issues = set(record.quality_issues)
    if "symbol_not_found" in issues:
        return "symbol_not_found"
    if "provider_error" in issues:
        return "provider_error"
    if record.unsupported_reason or not record.registry_found:
        return "unsupported_symbol"
    if record.quote_trust_tier == "development":
        return "development_only"
    if record.source in {"mock", "mock_fallback"} or record.selected_provider in {"mock", "mock_fallback"}:
        return "development_only"
    if record.last_price is None and record.price is None:
        return "missing_last_price"
    if record.quote_time is None:
        return "missing_quote_time"
    if record.base_quote_completeness == "missing":
        return "base_quote_missing"
    if record.is_stale:
        return "stale_reference"
    if not record.usable_for_reference:
        return "not_reference_usable"
    return "none"


def _not_rankable_status(reason: str) -> str:
    if reason == "symbol_not_found":
        return "symbol_not_found"
    if reason in {"provider_error", "stale_reference"}:
        return "provider_issue"
    if reason == "development_only":
        return "development_only"
    if reason in {"missing_last_price", "missing_quote_time", "base_quote_missing", "not_reference_usable", "unsupported_symbol"}:
        return "data_insufficient"
    return "not_rankable"


def _data_quality_score(record: PriceRecord) -> float:
    score = {
        "complete": 100.0,
        "partial": 70.0,
        "price_only": 40.0,
        "missing": 0.0,
    }.get(record.base_quote_completeness or "missing", 0.0)
    if record.is_stale:
        score -= 30
    if not record.usable_for_reference:
        score -= 40
    if record.quote_time is None:
        score -= 20
    return _clamp(score)


def _momentum_score(price_change_pct: float | None) -> float:
    if price_change_pct is None:
        return 50.0
    if price_change_pct < -3:
        return 35.0
    if price_change_pct < -1:
        return 45.0
    if price_change_pct <= 1:
        return 55.0
    if price_change_pct <= 3:
        return 70.0
    if price_change_pct <= 5:
        return 75.0
    return 60.0


def _field_reliability_score(status: str) -> float:
    return {
        "validated": 90.0,
        "provider_raw": 75.0,
        "unit_unknown": 55.0,
        "provider_dependent": 50.0,
        "not_validated": 35.0,
        "missing": 0.0,
        "development_only": 0.0,
    }.get(status or "missing", 50.0)


def _liquidity_score(record: PriceRecord) -> float:
    if record.amount_comparable_across_providers and record.amount_unit_confidence in {"high", "medium"} and record.amount is not None:
        return 65.0
    if record.volume_comparable_across_providers and record.volume_unit_confidence in {"high", "medium"} and record.volume is not None:
        return 55.0
    return 50.0


def _reconciliation_score(status: str) -> float:
    return {
        "aligned": 100.0,
        "minor_diff": 80.0,
        "single_source_only": 55.0,
        "warning_diff": 35.0,
        "major_diff": 0.0,
        "insufficient_data": 40.0,
        "provider_error": 30.0,
    }.get(status or "", 40.0)


def _watch_priority(score: float, record: PriceRecord) -> str:
    if record.source_agreement_status == "major_diff":
        return "low"
    if score >= 75:
        priority = "high"
    elif score >= 55:
        priority = "medium"
    else:
        priority = "low"
    if record.base_quote_completeness == "price_only" and priority == "high":
        return "medium"
    return priority


def _notes(record: PriceRecord, exclusion: str) -> str:
    notes: list[str] = []
    if exclusion != "none":
        notes.append(exclusion)
    if not record.amount_comparable_across_providers:
        notes.append("amount_not_comparable")
    if not record.volume_comparable_across_providers:
        notes.append("volume_not_comparable")
    if record.quote_trust_tier == "reference":
        notes.append("reference_only")
    if record.base_quote_completeness == "partial":
        notes.append("partial_base_quote")
    if record.price_change_pct is None:
        notes.append("missing_price_change_pct")
    elif record.price_change_pct > 5:
        notes.append("high_move_needs_intraday_confirmation")
    if record.source_agreement_status == "major_diff":
        notes.append("major_diff_needs_debug")
    if record.field_validation_status == "provider_raw":
        notes.append("provider_raw_units")
    if not notes:
        notes.append("data_quality_first")
    return ",".join(dict.fromkeys(notes))


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))
