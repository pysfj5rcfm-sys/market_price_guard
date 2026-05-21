from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from market_price_guard.intraday_metrics import IntradayInputs, build_intraday_outputs, calculate_intraday_metrics


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def _inputs(tmp_path: Path) -> IntradayInputs:
    return IntradayInputs(
        minute_probe_dir=tmp_path / "minute",
        tech_spot_dir=tmp_path / "tech",
        operation_candidate_dir=tmp_path / "candidates",
        output_dir=tmp_path / "intraday",
    )


def _spot_rows() -> list[dict[str, object]]:
    return [
        {
            "symbol": "159819.SZ",
            "name": "人工智能ETF",
            "last_price": 99.0,
            "price": 99.0,
            "quote_time": "2026-05-21T09:31:00+08:00",
            "selected_provider": "akshare",
            "source": "akshare",
            "quote_trust_tier": "operation",
            "usable_for_operation": True,
            "usable_for_reference": True,
            "required_for_operation": True,
            "role": "ai_tech_equity",
            "asset_type": "ETF",
            "report_group": "AI / 人工智能ETF",
        },
        {
            "symbol": "GOLD_CNY",
            "name": "黄金参考",
            "last_price": 520.0,
            "price": 520.0,
            "quote_time": "2026-05-21T09:31:00+08:00",
            "selected_provider": "manual",
            "source": "manual",
            "quote_trust_tier": "reference",
            "usable_for_operation": False,
            "usable_for_reference": True,
            "required_for_operation": False,
            "role": "defense_or_potential_tech_funding",
            "asset_type": "manual",
        },
    ]


@pytest.mark.unit
def test_reference_vwap_uses_close_volume_when_amount_missing(tmp_path):
    inputs = _inputs(tmp_path)
    _write_csv(inputs.tech_spot_dir / "prices_snapshot.csv", _spot_rows())
    _write_csv(
        inputs.minute_probe_dir / "minute_bars_snapshot.csv",
        [
            {"symbol": "159819.SZ", "name": "人工智能ETF", "provider": "akshare", "interval": "1m", "timestamp": "2026-05-21T09:30:00+08:00", "open": 10, "high": 12, "low": 9, "close": 10, "volume": 100, "amount": None, "validation_status": "provider_raw", "notes": ""},
            {"symbol": "159819.SZ", "name": "人工智能ETF", "provider": "akshare", "interval": "1m", "timestamp": "2026-05-21T09:31:00+08:00", "open": 10, "high": 12, "low": 9, "close": 12, "volume": 300, "amount": None, "validation_status": "provider_raw", "notes": ""},
        ],
    )

    rows = calculate_intraday_metrics(inputs)
    ai = next(row for row in rows if row["symbol"] == "159819.SZ")

    assert ai["reference_vwap"] == 11.5
    assert ai["reference_vwap_method"] == "close_volume_weighted"
    assert ai["reference_intraday_last"] == 12
    assert ai["distance_to_reference_vwap_pct"] == pytest.approx(4.347826)
    assert ai["minute_data_provider_raw"] is True
    assert ai["usable_for_operation"] is True


@pytest.mark.unit
def test_zero_volume_and_manual_are_not_calculable(tmp_path):
    inputs = _inputs(tmp_path)
    _write_csv(inputs.tech_spot_dir / "prices_snapshot.csv", _spot_rows())
    _write_csv(
        inputs.minute_probe_dir / "minute_bars_snapshot.csv",
        [
            {"symbol": "159819.SZ", "provider": "akshare", "interval": "1m", "timestamp": "2026-05-21T09:30:00+08:00", "open": 10, "high": 12, "low": 9, "close": 10, "volume": 0, "validation_status": "provider_raw"},
        ],
    )

    rows = calculate_intraday_metrics(inputs)
    ai = next(row for row in rows if row["symbol"] == "159819.SZ")
    gold = next(row for row in rows if row["symbol"] == "GOLD_CNY")

    assert ai["reference_intraday_status"] == "zero_volume"
    assert ai["reference_vwap"] is None
    assert gold["reference_intraday_status"] == "not_supported"
    assert gold["reference_vwap_note"] == "manual_price_only"


@pytest.mark.unit
def test_high_equals_low_keeps_vwap_but_position_not_calculable(tmp_path):
    inputs = _inputs(tmp_path)
    _write_csv(inputs.tech_spot_dir / "prices_snapshot.csv", _spot_rows())
    _write_csv(
        inputs.minute_probe_dir / "minute_bars_snapshot.csv",
        [
            {"symbol": "159819.SZ", "provider": "akshare", "interval": "1m", "timestamp": "2026-05-21T09:30:00+08:00", "open": 10, "high": 10, "low": 10, "close": 10, "volume": 100, "validation_status": "provider_raw"},
            {"symbol": "159819.SZ", "provider": "akshare", "interval": "1m", "timestamp": "2026-05-21T09:31:00+08:00", "open": 10, "high": 10, "low": 10, "close": 10, "volume": 100, "validation_status": "provider_raw"},
        ],
    )

    ai = next(row for row in calculate_intraday_metrics(inputs) if row["symbol"] == "159819.SZ")

    assert ai["reference_vwap"] == 10
    assert ai["intraday_position_pct"] is None
    assert ai["reference_intraday_status"] == "insufficient_intraday_range"


@pytest.mark.unit
def test_spot_minute_alignment_statuses(tmp_path):
    inputs = _inputs(tmp_path)
    spot = _spot_rows()
    spot[0]["quote_time"] = "2026-05-21T09:30:00+08:00"
    _write_csv(inputs.tech_spot_dir / "prices_snapshot.csv", spot)
    _write_csv(
        inputs.minute_probe_dir / "minute_bars_snapshot.csv",
        [
            {"symbol": "159819.SZ", "provider": "yfinance", "interval": "1m", "timestamp": "2026-05-21T09:40:00+08:00", "open": 10, "high": 12, "low": 9, "close": 12, "volume": 100, "validation_status": "provider_dependent"},
        ],
    )

    ai = next(row for row in calculate_intraday_metrics(inputs) if row["symbol"] == "159819.SZ")

    assert ai["spot_vs_minute_time_gap_seconds"] == 600
    assert ai["spot_minute_time_alignment_status"] == "spot_stale_minute_fresh"
    assert ai["minute_data_provider_dependent"] is True
    assert ai["minute_source_priority_rank"] == 3


@pytest.mark.unit
def test_no_minute_bars_snapshot_graceful_fallback(tmp_path):
    inputs = _inputs(tmp_path)
    _write_csv(inputs.tech_spot_dir / "prices_snapshot.csv", _spot_rows())

    rows = calculate_intraday_metrics(inputs)

    assert any(row["reference_intraday_status"] == "no_minute_bars" for row in rows if row["symbol"] != "GOLD_CNY")


@pytest.mark.contract
def test_intraday_outputs_are_generated_and_reference_only(tmp_path):
    inputs = _inputs(tmp_path)
    _write_csv(inputs.tech_spot_dir / "prices_snapshot.csv", _spot_rows())
    _write_csv(
        inputs.minute_probe_dir / "minute_bars_snapshot.csv",
        [
            {"symbol": "159819.SZ", "name": "人工智能ETF", "provider": "akshare", "interval": "1m", "timestamp": "2026-05-21T09:30:00+08:00", "open": 10, "high": 12, "low": 9, "close": 10, "volume": 100, "validation_status": "provider_raw"},
            {"symbol": "159819.SZ", "name": "人工智能ETF", "provider": "akshare", "interval": "1m", "timestamp": "2026-05-21T09:31:00+08:00", "open": 10, "high": 12, "low": 9, "close": 12, "volume": 300, "validation_status": "provider_raw"},
        ],
    )

    df = build_intraday_outputs(inputs)

    assert (inputs.output_dir / "intraday_metrics_snapshot.csv").exists()
    assert (inputs.output_dir / "reference_vwap_report.md").exists()
    assert "Reference VWAP is not operation-grade" in (inputs.output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    assert "Reference VWAP Report" in (inputs.output_dir / "reference_vwap_report.md").read_text(encoding="utf-8")
    assert "buy" not in (inputs.output_dir / "reference_vwap_report.md").read_text(encoding="utf-8").lower()
    ai = df[df["symbol"] == "159819.SZ"].iloc[0]
    assert ai["reference_vwap"] == 11.5


@pytest.mark.script
def test_intraday_metrics_script_contract():
    script = Path("scripts/run_tech_intraday_metrics.ps1").read_text(encoding="utf-8")
    assert "market_price_guard.intraday_metrics" in script
    assert "outputs_tech_intraday_latest" in script
    assert "--strict" not in script
