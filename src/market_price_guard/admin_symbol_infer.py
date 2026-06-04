from __future__ import annotations

import re
from typing import Any

from .admin_models import SymbolInference


SZ_PREFIXES = ("159", "002", "003", "300", "301")
SH_PREFIXES = ("510", "511", "512", "513", "515", "516", "517", "518", "588", "600", "601", "603", "605", "688")
ETF_PREFIXES = ("159", "510", "511", "512", "513", "515", "516", "517", "518", "588")
KNOWN_MANUAL = {"GOLD_CNY"}
SUFFIX_RE = re.compile(r"^([A-Z0-9]+)\.(SH|SZ|HK)$", re.IGNORECASE)
PURE_ALPHA_RE = re.compile(r"^[A-Z]{1,6}$")


def canonicalize_symbol(raw_symbol: str, registry: dict[str, Any] | None = None) -> SymbolInference:
    raw = str(raw_symbol or "").strip()
    normalized = raw.upper()
    registry = registry or {}
    if not normalized:
        return SymbolInference(raw_symbol=raw, canonical_symbol="", inferred_market="", inferred_asset_type="", status="ambiguous", reason="empty symbol")

    if normalized in registry:
        entry = dict(registry.get(normalized) or {})
        return SymbolInference(
            raw_symbol=raw,
            canonical_symbol=normalized,
            inferred_market=str(entry.get("market") or ""),
            inferred_asset_type=str(entry.get("asset_type") or ""),
            status="ok",
            reason="registry exact match",
        )

    match = SUFFIX_RE.match(normalized)
    if match:
        code, suffix = match.groups()
        return SymbolInference(
            raw_symbol=raw,
            canonical_symbol=f"{code}.{suffix.upper()}",
            inferred_market=suffix.upper(),
            inferred_asset_type=_asset_type_for_code(code, suffix.upper()),
            status="ok",
            reason="explicit suffix",
        )

    if normalized in KNOWN_MANUAL:
        return SymbolInference(
            raw_symbol=raw,
            canonical_symbol=normalized,
            inferred_market="MANUAL",
            inferred_asset_type="manual asset",
            status="ok",
            reason="manual asset",
        )

    if normalized.isdigit() and len(normalized) == 5:
        return SymbolInference(
            raw_symbol=raw,
            canonical_symbol=f"{normalized}.HK",
            inferred_market="HK",
            inferred_asset_type="HK stock / ETF",
            status="ok",
            reason="five digit HK code",
        )

    if normalized.isdigit() and len(normalized) == 6:
        suffix = _suffix_for_six_digit_code(normalized)
        if suffix:
            return SymbolInference(
                raw_symbol=raw,
                canonical_symbol=f"{normalized}.{suffix}",
                inferred_market=suffix,
                inferred_asset_type=_asset_type_for_code(normalized, suffix),
                status="ok",
                reason="A-share code prefix",
            )

    if PURE_ALPHA_RE.match(normalized):
        return SymbolInference(
            raw_symbol=raw,
            canonical_symbol=normalized,
            inferred_market="US",
            inferred_asset_type="US stock / ETF",
            status="ok",
            reason="global ticker without local suffix",
        )

    if "_" in normalized and normalized in registry:
        entry = dict(registry.get(normalized) or {})
        return SymbolInference(
            raw_symbol=raw,
            canonical_symbol=normalized,
            inferred_market=str(entry.get("market") or ""),
            inferred_asset_type=str(entry.get("asset_type") or ""),
            status="ok",
            reason="registry symbol with underscore",
        )

    return SymbolInference(
        raw_symbol=raw,
        canonical_symbol=normalized,
        inferred_market="",
        inferred_asset_type="",
        status="ambiguous",
        reason="market must be selected",
    )


def _suffix_for_six_digit_code(code: str) -> str:
    if code.startswith(SZ_PREFIXES):
        return "SZ"
    if code.startswith(SH_PREFIXES):
        return "SH"
    return ""


def _asset_type_for_code(code: str, suffix: str) -> str:
    if suffix == "HK":
        return "HK stock / ETF"
    if code.startswith(ETF_PREFIXES):
        return "ETF"
    if suffix in {"SH", "SZ"}:
        return "stock"
    return ""
