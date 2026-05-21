from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .symbol_registry import load_symbol_registry, load_universe


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
UNIVERSES_DIR = CONFIG_DIR / "universes"
REGISTRY_PATH = CONFIG_DIR / "symbol_registry.yaml"

DEFAULT_MINUTE_PROBE_DIR = PROJECT_ROOT / "outputs_tech_minute_probe_latest"
DEFAULT_TECH_SPOT_DIR = PROJECT_ROOT / "outputs_tech_latest"
DEFAULT_OPERATION_CANDIDATE_DIR = PROJECT_ROOT / "outputs_tech_operation_candidates_latest"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs_tech_intraday_latest"

INTRADAY_COLUMNS = [
    "symbol",
    "name",
    "role",
    "universe_type",
    "source_universe",
    "operation_candidate",
    "core_holding",
    "asset_type",
    "report_group",
    "reference_vwap",
    "reference_vwap_source",
    "reference_vwap_validation_status",
    "reference_vwap_method",
    "reference_vwap_bar_count",
    "reference_vwap_first_time",
    "reference_vwap_latest_time",
    "reference_vwap_coverage_status",
    "reference_vwap_note",
    "reference_intraday_open",
    "reference_intraday_high",
    "reference_intraday_low",
    "reference_intraday_last",
    "reference_intraday_last_time",
    "reference_intraday_last_source",
    "distance_to_reference_vwap_pct",
    "intraday_position_pct",
    "drawdown_from_intraday_high_pct",
    "rebound_from_intraday_low_pct",
    "spot_last_price",
    "spot_quote_time",
    "spot_selected_provider",
    "spot_quote_trust_tier",
    "spot_vs_minute_time_gap_seconds",
    "spot_minute_time_alignment_status",
    "minute_source_priority_rank",
    "minute_source_quality",
    "minute_data_provider_dependent",
    "minute_data_provider_raw",
    "reference_intraday_status",
    "reference_intraday_note",
    "quote_trust_tier",
    "usable_for_operation",
    "required_for_operation",
    "affect_core_strict",
    "debug_invalid_row_count",
    "debug_valid_row_count",
    "debug_volume_sum",
    "debug_source_file",
]

SOURCE_PRIORITY = {"akshare": 1, "eastmoney_direct": 2, "yfinance": 3}


@dataclass(frozen=True)
class IntradayInputs:
    minute_probe_dir: Path = DEFAULT_MINUTE_PROBE_DIR
    tech_spot_dir: Path = DEFAULT_TECH_SPOT_DIR
    operation_candidate_dir: Path = DEFAULT_OPERATION_CANDIDATE_DIR
    output_dir: Path = DEFAULT_OUTPUT_DIR
    registry_path: Path = REGISTRY_PATH
    universes_dir: Path = UNIVERSES_DIR


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reference intraday metrics from minute probe outputs.")
    parser.add_argument("--minute-probe-dir", type=Path, default=DEFAULT_MINUTE_PROBE_DIR)
    parser.add_argument("--tech-spot-dir", type=Path, default=DEFAULT_TECH_SPOT_DIR)
    parser.add_argument("--operation-candidate-dir", type=Path, default=DEFAULT_OPERATION_CANDIDATE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--universes-dir", type=Path, default=UNIVERSES_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    build_intraday_outputs(
        IntradayInputs(
            minute_probe_dir=args.minute_probe_dir,
            tech_spot_dir=args.tech_spot_dir,
            operation_candidate_dir=args.operation_candidate_dir,
            output_dir=args.output_dir,
            registry_path=args.registry,
            universes_dir=args.universes_dir,
        )
    )
    print(f"Generated reference intraday metrics in {args.output_dir}")
    return 0


def build_intraday_outputs(inputs: IntradayInputs) -> pd.DataFrame:
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    rows = calculate_intraday_metrics(inputs)
    df = pd.DataFrame(rows, columns=INTRADAY_COLUMNS)
    df.to_csv(inputs.output_dir / "intraday_metrics_snapshot.csv", index=False, encoding="utf-8-sig")

    runtime = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": "tech",
        "output_type": "reference_intraday_metrics",
        "strict": False,
        "source_minute_file": str(inputs.minute_probe_dir / "minute_bars_snapshot.csv"),
        "tech_spot_file": str(inputs.tech_spot_dir / "prices_snapshot.csv"),
        "operation_candidate_spot_file": str(inputs.operation_candidate_dir / "prices_snapshot.csv"),
    }
    (inputs.output_dir / "index.md").write_text(build_index_report(df, runtime), encoding="utf-8")
    (inputs.output_dir / "0_upload_bundle.md").write_text(build_upload_bundle(df, runtime), encoding="utf-8")
    (inputs.output_dir / "reference_vwap_report.md").write_text(build_reference_vwap_report(df, runtime), encoding="utf-8")
    (inputs.output_dir / "debug_bundle.md").write_text(build_debug_bundle(df, runtime), encoding="utf-8")
    (inputs.output_dir / "data_completeness_report.md").write_text(build_data_completeness_report(df), encoding="utf-8")
    (inputs.output_dir / "provider_capability_report.md").write_text(build_provider_capability_report(df), encoding="utf-8")
    (inputs.output_dir / "provider_health_report.md").write_text(build_provider_health_report(df), encoding="utf-8")
    (inputs.output_dir / "price_reconciliation_report.md").write_text(build_price_reconciliation_report(), encoding="utf-8")
    (inputs.output_dir / "runtime_diagnostics.md").write_text(build_runtime_diagnostics(runtime), encoding="utf-8")
    return df


def calculate_intraday_metrics(inputs: IntradayInputs) -> list[dict[str, Any]]:
    registry = load_symbol_registry(inputs.registry_path)
    core_spec = load_universe("tech_core", inputs.universes_dir)
    candidate_spec = load_universe("tech_operation_candidates", inputs.universes_dir)
    symbols: list[tuple[str, str]] = [(symbol, "tech_core") for symbol in core_spec.symbols]
    symbols.extend((symbol, "tech_operation_candidates") for symbol in candidate_spec.symbols)

    minute_df = _read_csv(inputs.minute_probe_dir / "minute_bars_snapshot.csv")
    tech_spot = _read_csv(inputs.tech_spot_dir / "prices_snapshot.csv")
    candidate_spot = _read_csv(inputs.operation_candidate_dir / "prices_snapshot.csv")
    minute_summary = _read_csv(inputs.minute_probe_dir / "prices_snapshot.csv")

    rows: list[dict[str, Any]] = []
    for symbol, source_universe in symbols:
        entry = registry.get(symbol, {})
        spot = _spot_row(symbol, source_universe, tech_spot, candidate_spot)
        minute_rows = _symbol_rows(minute_df, symbol)
        summary = _first_row(_symbol_rows(minute_summary, symbol))
        rows.append(_calculate_symbol_row(symbol, source_universe, entry, spot, minute_rows, summary, inputs))
    return rows


def _calculate_symbol_row(
    symbol: str,
    source_universe: str,
    entry: dict[str, Any],
    spot: dict[str, Any],
    minute_rows: pd.DataFrame,
    minute_summary: dict[str, Any],
    inputs: IntradayInputs,
) -> dict[str, Any]:
    core_holding = source_universe == "tech_core"
    operation_candidate = source_universe == "tech_operation_candidates"
    base = _base_row(symbol, source_universe, entry, spot, core_holding, operation_candidate, inputs)

    if symbol == "GOLD_CNY" or str(entry.get("asset_type", "")).lower() == "manual":
        return {
            **base,
            **_not_calculable_fields(
                "not_supported",
                "manual_price_only",
                validation_status="not_supported",
                source_quality="not_supported",
            ),
        }
    if minute_rows.empty:
        return {
            **base,
            **_not_calculable_fields(
                "no_minute_bars",
                _minute_missing_note(minute_summary),
                validation_status="not_calculable",
                source_quality="missing",
            ),
        }

    cleaned = _clean_minute_rows(minute_rows)
    valid = cleaned[(cleaned["close"].notna()) & (cleaned["volume"].notna()) & (cleaned["volume"] > 0)].copy()
    if valid.empty:
        return {
            **base,
            **_not_calculable_fields(
                "zero_volume",
                "not_calculable: zero_volume_or_missing_close",
                validation_status=_validation_status(minute_rows),
                source_quality=_source_quality(minute_rows),
                provider=_first_value(minute_rows, "provider"),
                interval=_first_value(minute_rows, "interval"),
                invalid_row_count=len(cleaned),
            ),
        }

    valid = valid.sort_values("timestamp")
    volume_sum = float(valid["volume"].sum())
    reference_vwap = float((valid["close"] * valid["volume"]).sum() / volume_sum)
    first = valid.iloc[0]
    last = valid.iloc[-1]
    high = _float_or_none(valid["high"].max())
    low = _float_or_none(valid["low"].min())
    last_close = _float_or_none(last["close"])
    latest_time = _timestamp_to_iso(last["timestamp"])
    first_time = _timestamp_to_iso(first["timestamp"])
    provider = _first_value(minute_rows, "provider")
    validation = _validation_status(minute_rows)
    source_quality = _source_quality(minute_rows)
    spot_time = _parse_dt(spot.get("quote_time"))
    minute_time = _parse_dt(latest_time)
    gap, alignment = _spot_minute_alignment(spot_time, minute_time)
    intraday_position: float | None = None
    status = "available"
    note = _short_note(provider, alignment)
    if high is not None and low is not None and high != low and last_close is not None:
        intraday_position = (last_close - low) / (high - low) * 100
    elif high == low:
        status = "insufficient_intraday_range"
        note = f"{note}; insufficient_intraday_range"

    return {
        **base,
        "reference_vwap": _round(reference_vwap),
        "reference_vwap_source": provider,
        "reference_vwap_validation_status": validation,
        "reference_vwap_method": "close_volume_weighted",
        "reference_vwap_bar_count": int(len(valid)),
        "reference_vwap_first_time": first_time,
        "reference_vwap_latest_time": latest_time,
        "reference_vwap_coverage_status": "available",
        "reference_vwap_note": "reference_only; close_volume_weighted; not_operation_grade",
        "reference_intraday_open": _float_or_none(first["open"]),
        "reference_intraday_high": high,
        "reference_intraday_low": low,
        "reference_intraday_last": last_close,
        "reference_intraday_last_time": latest_time,
        "reference_intraday_last_source": "minute_bar_latest_close",
        "distance_to_reference_vwap_pct": _pct(last_close - reference_vwap if last_close is not None else None, reference_vwap),
        "intraday_position_pct": _round(intraday_position),
        "drawdown_from_intraday_high_pct": _pct(last_close - high if high else None, high) if high else None,
        "rebound_from_intraday_low_pct": _pct(last_close - low if low else None, low) if low else None,
        "spot_vs_minute_time_gap_seconds": gap,
        "spot_minute_time_alignment_status": alignment,
        "minute_source_priority_rank": SOURCE_PRIORITY.get(provider),
        "minute_source_quality": source_quality,
        "minute_data_provider_dependent": provider in {"yfinance", "eastmoney_direct"} or validation == "provider_dependent",
        "minute_data_provider_raw": provider == "akshare" and validation == "provider_raw",
        "reference_intraday_status": status,
        "reference_intraday_note": note,
        "debug_invalid_row_count": int(len(cleaned) - len(valid)),
        "debug_valid_row_count": int(len(valid)),
        "debug_volume_sum": _round(volume_sum),
        "debug_source_file": str(inputs.minute_probe_dir / "minute_bars_snapshot.csv"),
    }


def _base_row(
    symbol: str,
    source_universe: str,
    entry: dict[str, Any],
    spot: dict[str, Any],
    core_holding: bool,
    operation_candidate: bool,
    inputs: IntradayInputs,
) -> dict[str, Any]:
    required = _bool_value(spot.get("required_for_operation"), bool(entry.get("required_for_operation", False)) and core_holding)
    usable = _bool_value(spot.get("usable_for_operation"), False)
    if operation_candidate:
        required = False
        usable = False
    return {
        "symbol": symbol,
        "name": str(spot.get("name") or entry.get("name") or symbol),
        "role": str(spot.get("role") or entry.get("role") or ""),
        "universe_type": "core_holdings" if core_holding else "operation_candidate",
        "source_universe": source_universe,
        "operation_candidate": operation_candidate,
        "core_holding": core_holding,
        "asset_type": str(spot.get("asset_type") or entry.get("asset_type") or ""),
        "report_group": str(spot.get("report_group") or entry.get("report_group") or ""),
        "spot_last_price": _float_or_none(spot.get("last_price")) or _float_or_none(spot.get("price")),
        "spot_quote_time": str(spot.get("quote_time") or ""),
        "spot_selected_provider": str(spot.get("selected_provider") or spot.get("source") or ""),
        "spot_quote_trust_tier": str(spot.get("quote_trust_tier") or ""),
        "quote_trust_tier": str(spot.get("quote_trust_tier") or "reference"),
        "usable_for_operation": usable,
        "required_for_operation": required,
        "affect_core_strict": core_holding and required,
    }


def _not_calculable_fields(
    status: str,
    note: str,
    validation_status: str,
    source_quality: str,
    provider: str = "",
    interval: str = "",
    invalid_row_count: int = 0,
) -> dict[str, Any]:
    return {
        "reference_vwap": None,
        "reference_vwap_source": provider,
        "reference_vwap_validation_status": validation_status,
        "reference_vwap_method": "",
        "reference_vwap_bar_count": 0,
        "reference_vwap_first_time": "",
        "reference_vwap_latest_time": "",
        "reference_vwap_coverage_status": status,
        "reference_vwap_note": note,
        "reference_intraday_open": None,
        "reference_intraday_high": None,
        "reference_intraday_low": None,
        "reference_intraday_last": None,
        "reference_intraday_last_time": "",
        "reference_intraday_last_source": "",
        "distance_to_reference_vwap_pct": None,
        "intraday_position_pct": None,
        "drawdown_from_intraday_high_pct": None,
        "rebound_from_intraday_low_pct": None,
        "spot_vs_minute_time_gap_seconds": None,
        "spot_minute_time_alignment_status": "unknown",
        "minute_source_priority_rank": SOURCE_PRIORITY.get(provider),
        "minute_source_quality": source_quality,
        "minute_data_provider_dependent": provider in {"yfinance", "eastmoney_direct"},
        "minute_data_provider_raw": provider == "akshare" and validation_status == "provider_raw",
        "reference_intraday_status": status,
        "reference_intraday_note": note,
        "debug_invalid_row_count": invalid_row_count,
        "debug_valid_row_count": 0,
        "debug_volume_sum": None,
        "debug_source_file": "",
    }


def build_index_report(df: pd.DataFrame, runtime: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# market_price_guard Reference Intraday Metrics Index",
            "",
            f"- generated_at: {runtime['generated_at']}",
            "- profile: tech",
            "- output_type: reference_intraday_metrics",
            "- strict: false",
            f"- total_symbols: {len(df)}",
            f"- vwap_calculable_count: {_count_status(df, 'available')}",
            "",
            "## Files",
            "- 0_upload_bundle.md",
            "- intraday_metrics_snapshot.csv",
            "- reference_vwap_report.md",
            "- debug_bundle.md",
            "- data_completeness_report.md",
            "- provider_capability_report.md",
            "- runtime_diagnostics.md",
        ]
    ) + "\n"


def build_upload_bundle(df: pd.DataFrame, runtime: dict[str, Any]) -> str:
    lines = [
        "# market_price_guard Reference Intraday Upload Bundle",
        "",
        "## Basic Info",
        "- profile: tech",
        "- output_type: reference_intraday_metrics",
        "- strict: false",
        "- purpose: reference-only",
        f"- generated_at: {runtime['generated_at']}",
        f"- source_minute_file: {runtime['source_minute_file']}",
        "",
        "## Safety Note",
        "- Reference VWAP is not operation-grade.",
        "- Intraday metrics do not change strict or usable_for_operation.",
        "- No trading advice is generated.",
        "",
        "## Reference Intraday Summary",
        "| symbol | name | universe | provider | validation | bars | latest_time | ref_vwap | last | dist_vwap_pct | pos_pct | spot_align | note |",
        "|---|---|---|---|---|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for _, row in df.iterrows():
        lines.append(
            "| {symbol} | {name} | {universe} | {provider} | {validation} | {bars} | {latest} | {vwap} | {last} | {dist} | {pos} | {align} | {note} |".format(
                symbol=row.get("symbol", ""),
                name=row.get("name", ""),
                universe=row.get("source_universe", ""),
                provider=row.get("reference_vwap_source", "") or "missing",
                validation=row.get("reference_vwap_validation_status", ""),
                bars=_fmt(row.get("reference_vwap_bar_count")),
                latest=row.get("reference_vwap_latest_time", ""),
                vwap=_fmt(row.get("reference_vwap")),
                last=_fmt(row.get("reference_intraday_last")),
                dist=_fmt(row.get("distance_to_reference_vwap_pct")),
                pos=_fmt(row.get("intraday_position_pct")),
                align=row.get("spot_minute_time_alignment_status", ""),
                note=_upload_note(row),
            )
        )
    if df.empty:
        lines.append("|  |  |  | missing | not_calculable | 0 |  |  |  |  |  | unknown | no_minute_bars |")
    return "\n".join(lines) + "\n"


def build_reference_vwap_report(df: pd.DataFrame, runtime: dict[str, Any]) -> str:
    lines = [
        "# Reference VWAP Report",
        "",
        "## Purpose / Scope",
        "- This report calculates reference VWAP and basic intraday position metrics from minute probe output.",
        "- VWAP is reference-only.",
        "- It is not a trading signal.",
        "- It does not upgrade operation readiness.",
        "- It does not replace QDII premium or IOPV checks.",
        "- For QDII ETFs, the premium module is still required before operation-level evaluation.",
        "",
        "## Source Priority",
        "1. AKShare",
        "2. Eastmoney Direct",
        "3. YFinance reference fallback",
        "",
        "## Core Holdings",
    ]
    lines.extend(_report_table(df[df["core_holding"] == True]))
    lines.extend(["", "## Operation Candidates"])
    lines.extend(_report_table(df[df["operation_candidate"] == True]))
    lines.extend(["", "## Not Calculable"])
    lines.extend(_not_calculable_table(df))
    lines.extend(["", "## Data Quality Notes"])
    lines.extend(_quality_notes(df))
    lines.extend(["", "## Safety Notes"])
    lines.extend(
        [
            "- Reference intraday metrics do not change strict.",
            "- Reference intraday metrics do not change quote_trust_tier or usable_for_operation.",
            "- No trading advice is generated.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_data_completeness_report(df: pd.DataFrame) -> str:
    lines = [
        "# Intraday Metrics Data Completeness Report",
        "",
        f"- total_symbols: {len(df)}",
        f"- core_symbols: {int(df['core_holding'].sum()) if not df.empty else 0}",
        f"- operation_candidate_symbols: {int(df['operation_candidate'].sum()) if not df.empty else 0}",
        f"- vwap_calculable_count: {_count_status(df, 'available')}",
        f"- no_minute_bars_count: {_count_status(df, 'no_minute_bars')}",
        f"- zero_volume_count: {_count_status(df, 'zero_volume')}",
        f"- manual_not_supported_count: {_count_status(df, 'not_supported')}",
        f"- provider_raw_count: {sum(1 for value in df.get('minute_source_quality', []) if value == 'provider_raw')}",
        f"- provider_dependent_count: {sum(1 for value in df.get('minute_source_quality', []) if value == 'provider_dependent')}",
        f"- akshare_count: {sum(1 for value in df.get('reference_vwap_source', []) if value == 'akshare')}",
        f"- eastmoney_count: {sum(1 for value in df.get('reference_vwap_source', []) if value == 'eastmoney_direct')}",
        f"- yfinance_count: {sum(1 for value in df.get('reference_vwap_source', []) if value == 'yfinance')}",
        f"- spot_stale_minute_fresh_count: {sum(1 for value in df.get('spot_minute_time_alignment_status', []) if value == 'spot_stale_minute_fresh')}",
        f"- aligned_count: {sum(1 for value in df.get('spot_minute_time_alignment_status', []) if value == 'aligned')}",
        f"- minute_stale_count: {sum(1 for value in df.get('spot_minute_time_alignment_status', []) if value == 'minute_stale')}",
        "",
        "Derived intraday fields are reference-only and do not change operation readiness.",
    ]
    return "\n".join(lines) + "\n"


def build_debug_bundle(df: pd.DataFrame, runtime: dict[str, Any]) -> str:
    lines = [
        "# Intraday Metrics Debug Bundle",
        "",
        f"- source_minute_file: {runtime['source_minute_file']}",
        f"- tech_spot_file: {runtime['tech_spot_file']}",
        f"- operation_candidate_spot_file: {runtime['operation_candidate_spot_file']}",
        "",
        "## Calculation Trace",
        "| symbol | source_universe | minute_rows | valid_rows | invalid_rows | volume_sum | vwap_method | high | low | last | spot_time | minute_time | alignment | reason |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---|---|---|---|",
    ]
    for _, row in df.iterrows():
        lines.append(
            "| {symbol} | {universe} | {minute_rows} | {valid_rows} | {invalid_rows} | {volume_sum} | {method} | {high} | {low} | {last} | {spot_time} | {minute_time} | {alignment} | {reason} |".format(
                symbol=row.get("symbol", ""),
                universe=row.get("source_universe", ""),
                minute_rows=row.get("reference_vwap_bar_count", 0),
                valid_rows=row.get("debug_valid_row_count", 0),
                invalid_rows=row.get("debug_invalid_row_count", 0),
                volume_sum=_fmt(row.get("debug_volume_sum")),
                method=row.get("reference_vwap_method", ""),
                high=_fmt(row.get("reference_intraday_high")),
                low=_fmt(row.get("reference_intraday_low")),
                last=_fmt(row.get("reference_intraday_last")),
                spot_time=row.get("spot_quote_time", ""),
                minute_time=row.get("reference_intraday_last_time", ""),
                alignment=row.get("spot_minute_time_alignment_status", ""),
                reason=row.get("reference_intraday_note", ""),
            )
        )
    return "\n".join(lines) + "\n"


def build_provider_capability_report(df: pd.DataFrame) -> str:
    return "\n".join(
        [
            "# Provider Capability Report",
            "",
            "## Intraday Metrics Capability",
            "- AKShare minute bars are treated as provider_raw reference data when available.",
            "- Eastmoney Direct minute bars are provider-dependent reference data when available.",
            "- YFinance minute bars are provider-dependent reference fallback data.",
            "- Reference VWAP does not upgrade operation readiness.",
            "",
            "## Source Counts",
            f"- akshare: {sum(1 for value in df.get('reference_vwap_source', []) if value == 'akshare')}",
            f"- eastmoney_direct: {sum(1 for value in df.get('reference_vwap_source', []) if value == 'eastmoney_direct')}",
            f"- yfinance: {sum(1 for value in df.get('reference_vwap_source', []) if value == 'yfinance')}",
        ]
    ) + "\n"


def build_provider_health_report(df: pd.DataFrame) -> str:
    return "\n".join(
        [
            "# Provider Health Report",
            "",
            "This intraday report reads existing minute probe artifacts and does not call providers.",
            f"- symbols_with_reference_vwap: {_count_status(df, 'available')}",
            f"- symbols_without_minute_bars: {_count_status(df, 'no_minute_bars')}",
        ]
    ) + "\n"


def build_price_reconciliation_report() -> str:
    return "# Price Reconciliation Report\n\nReference intraday metrics do not perform price reconciliation.\n"


def build_runtime_diagnostics(runtime: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Runtime Diagnostics",
            "",
            f"- generated_at: {runtime['generated_at']}",
            "- provider_calls: 0",
            "- note: intraday metrics read existing CSV artifacts only.",
        ]
    ) + "\n"


def _report_table(df: pd.DataFrame) -> list[str]:
    lines = [
        "| symbol | name | provider | bars | ref_vwap | last | dist_vwap_pct | pos_pct | spot_align | status | note |",
        "|---|---|---|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"| {row.get('symbol', '')} | {row.get('name', '')} | {row.get('reference_vwap_source', '') or 'missing'} | {_fmt(row.get('reference_vwap_bar_count'))} | {_fmt(row.get('reference_vwap'))} | {_fmt(row.get('reference_intraday_last'))} | {_fmt(row.get('distance_to_reference_vwap_pct'))} | {_fmt(row.get('intraday_position_pct'))} | {row.get('spot_minute_time_alignment_status', '')} | {row.get('reference_intraday_status', '')} | {_upload_note(row)} |"
        )
    if df.empty:
        lines.append("|  |  | missing | 0 |  |  |  |  | unknown | no_symbols |  |")
    return lines


def _not_calculable_table(df: pd.DataFrame) -> list[str]:
    scoped = df[df["reference_intraday_status"] != "available"] if not df.empty else df
    lines = ["| symbol | name | status | note |", "|---|---|---|---|"]
    for _, row in scoped.iterrows():
        lines.append(f"| {row.get('symbol', '')} | {row.get('name', '')} | {row.get('reference_intraday_status', '')} | {row.get('reference_intraday_note', '')} |")
    if scoped.empty:
        lines.append("|  |  | none | all calculable |")
    return lines


def _quality_notes(df: pd.DataFrame) -> list[str]:
    return [
        f"- provider_raw_count: {sum(1 for value in df.get('minute_source_quality', []) if value == 'provider_raw')}",
        f"- provider_dependent_count: {sum(1 for value in df.get('minute_source_quality', []) if value == 'provider_dependent')}",
        "- amount/volume units remain provider artifacts; this module uses close-volume weighting unless native amount/volume confidence is explicit.",
        "- Spot quotes are displayed for alignment checks; distance to reference VWAP uses minute-bar latest close.",
    ]


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _symbol_rows(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if df.empty or "symbol" not in df.columns:
        return pd.DataFrame()
    return df[df["symbol"].astype(str) == symbol].copy()


def _spot_row(symbol: str, source_universe: str, tech_spot: pd.DataFrame, candidate_spot: pd.DataFrame) -> dict[str, Any]:
    source = candidate_spot if source_universe == "tech_operation_candidates" else tech_spot
    row = _first_row(_symbol_rows(source, symbol))
    if row:
        return row
    return _first_row(_symbol_rows(tech_spot, symbol))


def _first_row(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {}
    return dict(df.iloc[0])


def _clean_minute_rows(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    for column in ["open", "high", "low", "close", "volume", "amount"]:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
        else:
            cleaned[column] = pd.NA
    cleaned["timestamp"] = pd.to_datetime(cleaned.get("timestamp"), errors="coerce")
    cleaned = cleaned[cleaned["timestamp"].notna()]
    return cleaned


def _validation_status(df: pd.DataFrame) -> str:
    value = _first_value(df, "validation_status")
    return value or "not_calculable"


def _source_quality(df: pd.DataFrame) -> str:
    provider = _first_value(df, "provider")
    validation = _validation_status(df)
    if provider == "akshare" and validation == "provider_raw":
        return "provider_raw"
    if provider in {"yfinance", "eastmoney_direct"} or validation == "provider_dependent":
        return "provider_dependent"
    return validation or "missing"


def _first_value(df: pd.DataFrame, column: str) -> str:
    if df.empty or column not in df.columns:
        return ""
    value = df[column].dropna()
    if value.empty:
        return ""
    return str(value.iloc[0])


def _minute_missing_note(summary: dict[str, Any]) -> str:
    status = str(summary.get("minute_bar_status") or "no_minute_bars")
    reason = str(summary.get("minute_bar_missing_reason") or "no_minute_bars")
    provider = str(summary.get("minute_bar_provider") or "missing")
    if status == "available":
        return "minute summary was available but snapshot rows are missing"
    return f"{status}: {reason}; provider={provider}"


def _spot_minute_alignment(spot_time: datetime | None, minute_time: datetime | None) -> tuple[float | None, str]:
    if spot_time is None or minute_time is None:
        return None, "unknown"
    delta = (minute_time - spot_time).total_seconds()
    gap = abs(delta)
    if gap <= 180:
        return round(gap, 3), "aligned"
    if delta > 180:
        return round(gap, 3), "spot_stale_minute_fresh"
    return round(gap, 3), "minute_stale"


def _parse_dt(value: object) -> datetime | None:
    if value in {"", None} or pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    if isinstance(parsed, pd.Timestamp):
        if parsed.tzinfo is None:
            parsed = parsed.tz_localize("Asia/Shanghai")
        return parsed.to_pydatetime()
    return None


def _timestamp_to_iso(value: object) -> str:
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is None:
            value = value.tz_localize("Asia/Shanghai")
        return value.isoformat()
    return str(value or "")


def _pct(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return _round(numerator / denominator * 100)


def _float_or_none(value: object) -> float | None:
    if value in {"", None}:
        return None
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)


def _bool_value(value: object, default: bool) -> bool:
    if value in {"", None} or pd.isna(value):
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _fmt(value: object) -> str:
    if value in {"", None}:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _upload_note(row: pd.Series) -> str:
    status = str(row.get("reference_intraday_status", ""))
    provider = str(row.get("reference_vwap_source", ""))
    alignment = str(row.get("spot_minute_time_alignment_status", ""))
    if status == "available":
        if provider == "akshare":
            return f"akshare_ref_ok; {alignment}".strip("; ")
        if provider == "yfinance":
            return f"yf_ref_provider_dependent; {alignment}".strip("; ")
        if provider == "eastmoney_direct":
            return f"eastmoney_ref_provider_dependent; {alignment}".strip("; ")
    if status == "not_supported":
        return "manual_not_supported"
    if status == "zero_volume":
        return "zero_volume; not_calculable"
    if status == "no_minute_bars":
        return "no_minute_bars"
    if status == "insufficient_intraday_range":
        return "insufficient_intraday_range"
    return status or "not_calculable"


def _short_note(provider: str, alignment: str) -> str:
    if provider == "akshare":
        return f"akshare_ref_ok; {alignment}"
    if provider == "yfinance":
        return f"yf_ref_provider_dependent; {alignment}"
    if provider == "eastmoney_direct":
        return f"eastmoney_ref_provider_dependent; {alignment}"
    return alignment


def _count_status(df: pd.DataFrame, status: str) -> int:
    if df.empty or "reference_vwap_coverage_status" not in df.columns:
        return 0
    return int((df["reference_vwap_coverage_status"] == status).sum())


if __name__ == "__main__":
    raise SystemExit(main())
