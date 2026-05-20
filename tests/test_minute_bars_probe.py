from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

import market_price_guard.minute_bars as minute_bars
from market_price_guard.main import parse_args, run_pipeline
from market_price_guard.models import PriceRecord
from market_price_guard.minute_bars import apply_minute_bars_probe
from market_price_guard.report import (
    build_upload_bundle,
    build_completeness_report,
    build_debug_bundle,
    build_provider_health_report,
)


MINUTE_COLUMNS = [
    "minute_bars_available",
    "minute_bar_provider",
    "minute_bar_interval",
    "minute_bar_count",
    "minute_bar_latest_time",
    "minute_bar_fetch_time",
    "minute_bar_status",
    "minute_bar_validation_status",
    "minute_bar_missing_reason",
    "minute_bar_notes",
    "minute_bar_market_session",
    "minute_bar_after_close_possible",
    "minute_bar_retry_suggested",
    "minute_bar_retry_reason",
    "minute_bar_after_close_applies_to",
    "minute_bar_upload_note",
    "yfinance_ticker",
]


def test_price_record_contains_minute_bar_probe_fields():
    fields = PriceRecord.model_fields
    for column in MINUTE_COLUMNS:
        assert column in fields


def test_cli_accepts_include_minute_bars_aliases():
    assert parse_args(["--include-minute-bars"]).include_minute_bars is True
    assert parse_args(["--minute-bars-probe"]).include_minute_bars is True


def _minute_record(symbol: str = "588200.SH") -> PriceRecord:
    return PriceRecord(
        project="tech",
        symbol=symbol,
        name="Probe ETF",
        market="CN",
        price=1.22,
        currency="CNY",
        source="akshare",
        selected_provider="akshare",
        quote_time=None,
        fetch_time=None,
        market_status="open",
        is_stale=False,
        usable_for_reference=True,
        quote_trust_tier="reference",
        usable_for_operation=False,
        required_for_operation=False,
    )


def test_minute_probe_outputs_reports_and_csv_columns(tmp_path):
    output_dir = tmp_path / "minute_probe"
    result = run_pipeline(
        output_dir=output_dir,
        provider_mode="mock",
        profile="tech",
        quote_purpose="reference",
        include_minute_bars=True,
    )

    assert result.exit_code == 0
    snapshot = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")
    for column in MINUTE_COLUMNS:
        assert column in snapshot.columns

    assert (output_dir / "minute_bars_snapshot.csv").exists()
    assert "Minute Bars Probe Summary" in (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    assert "Minute Bars Probe Detail" in (output_dir / "debug_bundle.md").read_text(encoding="utf-8")
    assert "Minute Bars Completeness" in (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")
    assert "Minute Bars Capability" in (output_dir / "provider_capability_report.md").read_text(encoding="utf-8")


def test_akshare_minute_probe_maps_etf_minute_dataframe(monkeypatch):
    class FakeAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            assert symbol == "588200"
            assert period == "1"
            return pd.DataFrame(
                [
                    {
                        "时间": "2026-05-20 10:01:00",
                        "开盘": 1.20,
                        "最高": 1.23,
                        "最低": 1.19,
                        "收盘": 1.22,
                        "成交量": 1000,
                        "成交额": 1220,
                    }
                ]
            )

    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FakeAk)
    record = PriceRecord(
        project="tech",
        symbol="588200.SH",
        name="Chip ETF",
        market="CN",
        price=1.22,
        currency="CNY",
        source="akshare",
        selected_provider="akshare",
        quote_time=None,
        fetch_time=None,
        market_status="open",
        is_stale=False,
        usable_for_reference=True,
        quote_trust_tier="reference",
        usable_for_operation=False,
        required_for_operation=False,
    )

    records, rows = apply_minute_bars_probe([record], include_minute_bars=True, provider_mode="live")

    assert records[0].minute_bars_available is True
    assert records[0].minute_bar_provider == "akshare"
    assert records[0].minute_bar_interval == "1m"
    assert records[0].minute_bar_count == 1
    assert records[0].minute_bar_status == "available"
    assert rows[0]["symbol"] == "588200.SH"
    assert rows[0]["close"] == 1.22


def test_akshare_minute_probe_empty_and_exception(monkeypatch):
    class EmptyAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            return pd.DataFrame()

    base_record = PriceRecord(
        project="tech",
        symbol="588200.SH",
        name="Chip ETF",
        market="CN",
        price=1.22,
        currency="CNY",
        source="akshare",
        selected_provider="akshare",
        quote_time=None,
        fetch_time=None,
        market_status="open",
        is_stale=False,
        usable_for_reference=True,
        quote_trust_tier="reference",
        usable_for_operation=False,
        required_for_operation=False,
    )

    def failing_eastmoney(secid, klt):
        raise ConnectionError("eastmoney down")

    monkeypatch.setattr(minute_bars, "_call_eastmoney_minute_bars", failing_eastmoney)
    monkeypatch.setattr(minute_bars, "_call_yfinance_minute_bars", lambda ticker, period, interval: (_ for _ in ()).throw(ConnectionError("yfinance down")))
    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: EmptyAk)
    empty_records, _rows = apply_minute_bars_probe([base_record], include_minute_bars=True, provider_mode="live")
    assert empty_records[0].minute_bar_provider == "yfinance"
    assert empty_records[0].minute_bar_status == "provider_error"
    assert "akshare_reason=empty_response" in empty_records[0].minute_bar_notes
    assert "eastmoney_status=provider_error" in empty_records[0].minute_bar_notes

    class FailingAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            raise ConnectionError("down")

    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FailingAk)
    failed_records, _rows = apply_minute_bars_probe([base_record], include_minute_bars=True, provider_mode="live")
    assert failed_records[0].minute_bar_provider == "yfinance"
    assert failed_records[0].minute_bar_status == "provider_error"
    assert failed_records[0].minute_bar_missing_reason == "provider_error"


def test_eastmoney_secid_mapping_and_minute_parse(monkeypatch):
    assert minute_bars.eastmoney_secid_for_symbol("513300.SH") == "1.513300"
    assert minute_bars.eastmoney_secid_for_symbol("588200.SH") == "1.588200"
    assert minute_bars.eastmoney_secid_for_symbol("159632.SZ") == "0.159632"
    assert minute_bars.eastmoney_secid_for_symbol("300308.SZ") == "0.300308"

    class FailingAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            raise ConnectionError("akshare down")

    def eastmoney_success(secid, klt):
        assert secid == "1.588200"
        return {"data": {"klines": ["2026-05-20 10:01,1.20,1.22,1.23,1.19,1000,1220"]}}

    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FailingAk)
    monkeypatch.setattr(minute_bars, "_call_eastmoney_minute_bars", eastmoney_success)
    record = PriceRecord(
        project="tech",
        symbol="588200.SH",
        name="Chip ETF",
        market="CN",
        price=1.22,
        currency="CNY",
        source="akshare",
        selected_provider="akshare",
        quote_time=None,
        fetch_time=None,
        market_status="open",
        is_stale=False,
        usable_for_reference=True,
        quote_trust_tier="reference",
        usable_for_operation=False,
        required_for_operation=False,
    )

    records, rows = apply_minute_bars_probe([record], include_minute_bars=True, provider_mode="live")

    assert records[0].minute_bars_available is True
    assert records[0].minute_bar_provider == "eastmoney_direct"
    assert records[0].minute_bar_interval == "1m"
    assert records[0].minute_bar_validation_status == "provider_dependent"
    assert "eastmoney_secid=1.588200" in records[0].minute_bar_notes
    assert rows[0]["provider"] == "eastmoney_direct"
    assert rows[0]["close"] == 1.22


def test_eastmoney_minute_empty_exception_parse_and_bad_symbol(monkeypatch):
    class FailingAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            raise ConnectionError("akshare down")

    base_record = PriceRecord(
        project="tech",
        symbol="588200.SH",
        name="Chip ETF",
        market="CN",
        price=1.22,
        currency="CNY",
        source="akshare",
        selected_provider="akshare",
        quote_time=None,
        fetch_time=None,
        market_status="open",
        is_stale=False,
        usable_for_reference=True,
        quote_trust_tier="reference",
        usable_for_operation=False,
        required_for_operation=False,
    )

    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FailingAk)
    monkeypatch.setattr(minute_bars, "_call_yfinance_minute_bars", lambda ticker, period, interval: (_ for _ in ()).throw(ConnectionError("yfinance down")))
    monkeypatch.setattr(minute_bars, "_call_eastmoney_minute_bars", lambda secid, klt: {"data": {"klines": []}})
    empty_records, _rows = apply_minute_bars_probe([base_record], include_minute_bars=True, provider_mode="live")
    assert empty_records[0].minute_bar_status == "provider_error"
    assert "eastmoney_reason=empty_response" in empty_records[0].minute_bar_notes

    monkeypatch.setattr(minute_bars, "_call_eastmoney_minute_bars", lambda secid, klt: {"data": {"klines": ["bad"]}})
    parse_records, _rows = apply_minute_bars_probe([base_record], include_minute_bars=True, provider_mode="live")
    assert parse_records[0].minute_bar_status == "provider_error"
    assert "eastmoney_reason=parse_error" in parse_records[0].minute_bar_notes

    monkeypatch.setattr(minute_bars, "_call_eastmoney_minute_bars", lambda secid, klt: (_ for _ in ()).throw(ConnectionError("down")))
    error_records, _rows = apply_minute_bars_probe([base_record], include_minute_bars=True, provider_mode="live")
    assert error_records[0].minute_bar_status == "provider_error"

    bad_record = base_record.model_copy(update={"symbol": "BAD"})
    bad_snapshot = minute_bars._eastmoney_snapshot(bad_record, minute_bars.datetime.now(minute_bars.timezone.utc))
    assert bad_snapshot.missing_reason == "secid_mapping_failed"


def test_minute_probe_counts_and_eastmoney_error_detail_are_consistent(monkeypatch):
    class FailingAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            raise ConnectionError("akshare remote closed")

    def failing_eastmoney(secid, klt):
        raise TimeoutError("eastmoney timeout detail that should be shortened")

    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FailingAk)
    monkeypatch.setattr(minute_bars, "_call_eastmoney_minute_bars", failing_eastmoney)

    after_close = datetime(2026, 5, 20, 16, 0, tzinfo=timezone(timedelta(hours=8)))
    records, _rows = apply_minute_bars_probe(
        [_minute_record()],
        include_minute_bars=True,
        provider_mode="live",
        now=after_close,
    )

    report = build_completeness_report(records, {"include_minute_bars": True})
    debug = build_debug_bundle(records, Path("."), runtime={"include_minute_bars": True})

    assert "- akshare_attempted_count: 1" in report
    assert "- akshare_error_count: 1" in report
    assert "- eastmoney_attempted_count: 1" in report
    assert "- eastmoney_error_count: 1" in report
    assert "- after_close_possible_count: 1" in report
    assert "- retry_during_trading_hours_count: 1" in report
    assert records[0].minute_bar_market_session == "cn_after_close"
    assert records[0].minute_bar_after_close_possible is True
    assert records[0].minute_bar_retry_suggested == "rerun_during_cn_trading_hours"
    assert "eastmoney_error_type" in debug
    assert "TimeoutError" in debug
    assert "eastmoney_error_message" in debug


def test_minute_probe_success_counts_and_trading_hours_diagnostic(monkeypatch):
    class FakeAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            return pd.DataFrame(
                [
                    {
                        "datetime": "2026-05-20 10:01:00",
                        "open": 1.20,
                        "high": 1.23,
                        "low": 1.19,
                        "close": 1.22,
                    }
                ]
            )

    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FakeAk)
    trading_time = datetime(2026, 5, 20, 10, 0, tzinfo=timezone(timedelta(hours=8)))
    records, _rows = apply_minute_bars_probe(
        [_minute_record()],
        include_minute_bars=True,
        provider_mode="live",
        now=trading_time,
    )
    report = build_completeness_report(records, {"include_minute_bars": True})

    assert "- akshare_attempted_count: 1" in report
    assert "- akshare_success_count: 1" in report
    assert records[0].minute_bar_market_session == "cn_trading_hours"
    assert records[0].minute_bar_after_close_possible is False
    assert records[0].quote_trust_tier == "reference"
    assert records[0].usable_for_operation is False


def test_minute_probe_trading_hours_provider_error_not_after_close(monkeypatch):
    class FailingAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            raise ConnectionError("akshare down")

    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FailingAk)
    monkeypatch.setattr(minute_bars, "_call_eastmoney_minute_bars", lambda secid, klt: (_ for _ in ()).throw(ConnectionError("eastmoney down")))

    trading_time = datetime(2026, 5, 20, 10, 0, tzinfo=timezone(timedelta(hours=8)))
    records, _rows = apply_minute_bars_probe(
        [_minute_record()],
        include_minute_bars=True,
        provider_mode="live",
        now=trading_time,
    )

    assert records[0].minute_bar_market_session == "cn_trading_hours"
    assert records[0].minute_bar_after_close_possible is False
    assert records[0].minute_bar_retry_suggested == "retry_or_try_fallback_provider"


def test_yfinance_fallback_is_not_attempted_when_akshare_succeeds(monkeypatch):
    class FakeAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            return pd.DataFrame([{"datetime": "2026-05-20 10:01:00", "close": 1.22}])

    calls = {"yfinance": 0, "eastmoney": 0}
    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FakeAk)
    monkeypatch.setattr(minute_bars, "_call_eastmoney_minute_bars", lambda secid, klt: calls.__setitem__("eastmoney", calls["eastmoney"] + 1))
    monkeypatch.setattr(minute_bars, "_call_yfinance_minute_bars", lambda ticker, period, interval: calls.__setitem__("yfinance", calls["yfinance"] + 1))

    records, _rows = apply_minute_bars_probe([_minute_record()], include_minute_bars=True, provider_mode="live")

    assert records[0].minute_bar_provider == "akshare"
    assert calls == {"yfinance": 0, "eastmoney": 0}


def test_yfinance_fallback_is_not_attempted_when_eastmoney_succeeds(monkeypatch):
    class FailingAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            raise ConnectionError("akshare down")

    calls = {"yfinance": 0}
    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FailingAk)
    monkeypatch.setattr(
        minute_bars,
        "_call_eastmoney_minute_bars",
        lambda secid, klt: {"data": {"klines": ["2026-05-20 10:01,1.20,1.22,1.23,1.19,1000,1220"]}},
    )
    monkeypatch.setattr(minute_bars, "_call_yfinance_minute_bars", lambda ticker, period, interval: calls.__setitem__("yfinance", calls["yfinance"] + 1))

    records, _rows = apply_minute_bars_probe([_minute_record()], include_minute_bars=True, provider_mode="live")

    assert records[0].minute_bar_provider == "eastmoney_direct"
    assert calls["yfinance"] == 0


def test_yfinance_reference_fallback_success_writes_rows_and_preserves_semantics(monkeypatch):
    class FailingAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            raise ConnectionError("akshare down")

    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FailingAk)
    monkeypatch.setattr(minute_bars, "_call_eastmoney_minute_bars", lambda secid, klt: (_ for _ in ()).throw(ConnectionError("eastmoney down")))

    def yfinance_success(ticker, period, interval):
        assert ticker == "588200.SS"
        assert interval == "1m"
        return pd.DataFrame(
            [{"Open": 1.20, "High": 1.23, "Low": 1.19, "Close": 1.22, "Volume": 1000}],
            index=[pd.Timestamp("2026-05-20 10:01:00", tz="Asia/Shanghai")],
        )

    monkeypatch.setattr(minute_bars, "_call_yfinance_minute_bars", yfinance_success)

    records, rows = apply_minute_bars_probe([_minute_record()], include_minute_bars=True, provider_mode="live")

    assert records[0].minute_bars_available is True
    assert records[0].minute_bar_provider == "yfinance"
    assert records[0].minute_bar_validation_status == "provider_dependent"
    assert records[0].yfinance_ticker == "588200.SS"
    assert records[0].minute_bar_after_close_applies_to in {"", "akshare,eastmoney_direct"}
    assert len(records[0].minute_bar_upload_note) <= 120
    assert "provider_attempted=akshare,eastmoney_direct,yfinance" in records[0].minute_bar_notes
    assert "provider_success=yfinance" in records[0].minute_bar_notes
    assert "not_operation_grade" in records[0].minute_bar_notes
    assert records[0].quote_trust_tier == "reference"
    assert records[0].usable_for_operation is False
    assert rows[0]["provider"] == "yfinance"


def test_upload_bundle_uses_compact_minute_note_and_debug_keeps_details(monkeypatch, tmp_path):
    class FailingAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            raise ConnectionError("RemoteDisconnected endpoint detail")

    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FailingAk)
    monkeypatch.setattr(minute_bars, "_call_eastmoney_minute_bars", lambda secid, klt: (_ for _ in ()).throw(ConnectionError("RemoteDisconnected https://push2his.eastmoney.com/detail")))
    monkeypatch.setattr(
        minute_bars,
        "_call_yfinance_minute_bars",
        lambda ticker, period, interval: pd.DataFrame(
            [{"Open": 1.20, "High": 1.23, "Low": 1.19, "Close": 1.22, "Volume": 1000}],
            index=[pd.Timestamp("2026-05-20 10:01:00", tz="Asia/Shanghai")],
        ),
    )

    records, _rows = apply_minute_bars_probe([_minute_record()], include_minute_bars=True, provider_mode="live")
    upload = build_upload_bundle(records, tmp_path, provider_mode="live", runtime={"include_minute_bars": True, "profile": "tech"})
    debug = build_debug_bundle(records, tmp_path, provider_mode="live", runtime={"include_minute_bars": True})
    snapshot = pd.DataFrame([record.output_dict() for record in records])

    assert "Minute note is compact" in upload
    assert "yf_ref_ok" in upload
    assert "provider_dependent" in upload
    assert "not_operation_grade" in upload
    assert "RemoteDisconnected" not in upload
    assert "push2his.eastmoney.com" not in upload
    assert "RemoteDisconnected" in debug
    assert "eastmoney_error_message" in debug
    assert "yfinance_status" in debug
    assert "akshare_error_message" in debug
    assert "minute_bar_notes" in snapshot.columns
    assert "minute_bar_upload_note" in snapshot.columns
    assert records[0].minute_bar_upload_note


def test_upload_bundle_all_minute_providers_failed_note_is_short(monkeypatch, tmp_path):
    class FailingAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            raise ConnectionError("akshare down")

    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FailingAk)
    monkeypatch.setattr(minute_bars, "_call_eastmoney_minute_bars", lambda secid, klt: (_ for _ in ()).throw(ConnectionError("eastmoney down")))
    monkeypatch.setattr(minute_bars, "_call_yfinance_minute_bars", lambda ticker, period, interval: (_ for _ in ()).throw(ConnectionError("yfinance down")))

    records, _rows = apply_minute_bars_probe([_minute_record()], include_minute_bars=True, provider_mode="live")
    upload = build_upload_bundle(records, tmp_path, provider_mode="live", runtime={"include_minute_bars": True, "profile": "tech"})

    assert "all_minute_providers_failed; see_debug" in upload
    assert "akshare down" not in upload
    assert "eastmoney down" not in upload
    assert "yfinance down" not in upload


def test_yfinance_reference_fallback_empty_exception_and_parse(monkeypatch):
    class FailingAk:
        @staticmethod
        def fund_etf_hist_min_em(symbol, period, adjust=""):
            raise ConnectionError("akshare down")

    monkeypatch.setattr(minute_bars, "_import_akshare", lambda: FailingAk)
    monkeypatch.setattr(minute_bars, "_call_eastmoney_minute_bars", lambda secid, klt: (_ for _ in ()).throw(ConnectionError("eastmoney down")))
    base = [_minute_record()]

    monkeypatch.setattr(minute_bars, "_call_yfinance_minute_bars", lambda ticker, period, interval: pd.DataFrame())
    empty_records, _rows = apply_minute_bars_probe(base, include_minute_bars=True, provider_mode="live")
    assert empty_records[0].minute_bar_provider == "yfinance"
    assert empty_records[0].minute_bar_missing_reason == "empty_response"

    monkeypatch.setattr(
        minute_bars,
        "_call_yfinance_minute_bars",
        lambda ticker, period, interval: pd.DataFrame([{"Close": None}], index=["bad_time"]),
    )
    parse_records, _rows = apply_minute_bars_probe(base, include_minute_bars=True, provider_mode="live")
    assert parse_records[0].minute_bar_status == "parse_error"
    assert parse_records[0].minute_bar_missing_reason == "parse_error"

    monkeypatch.setattr(minute_bars, "_call_yfinance_minute_bars", lambda ticker, period, interval: (_ for _ in ()).throw(RuntimeError("yf down")))
    error_records, _rows = apply_minute_bars_probe(base, include_minute_bars=True, provider_mode="live")
    assert error_records[0].minute_bar_status == "provider_error"
    assert "yfinance_error_type=RuntimeError" in error_records[0].minute_bar_notes


def test_yfinance_ticker_mapping_follows_quote_mapping():
    assert minute_bars._yfinance_minute_ticker_for_symbol("513300.SH") == "513300.SS"
    assert minute_bars._yfinance_minute_ticker_for_symbol("159632.SZ") == "159632.SZ"
    assert minute_bars._yfinance_minute_ticker_for_symbol("588200.SH") == "588200.SS"


def test_provider_health_sections_do_not_mix_fallback_functions():
    yfinance_record = _minute_record("159819.SZ").model_copy(
        update={
            "source": "yfinance",
            "selected_provider": "yfinance",
            "provider_diagnostics": {
                "function_name": "yfinance.Ticker",
                "status": "success",
                "returned_rows": 1,
            },
        }
    )
    eastmoney_record = _minute_record("588200.SH").model_copy(
        update={
            "source": "yfinance",
            "selected_provider": "yfinance",
            "provider_diagnostics": {
                "provider_attempts": [
                    {
                        "function_name": "eastmoney_direct.stock_get",
                        "status": "fail",
                        "exception_type": "ConnectionError",
                        "exception_message": "closed",
                    },
                    {
                        "function_name": "yfinance.Ticker",
                        "status": "success",
                        "returned_rows": 1,
                    },
                ]
            },
        }
    )
    akshare_minute_record = _minute_record("513300.SH").model_copy(
        update={
            "minute_bar_provider": "eastmoney_direct",
            "minute_bar_status": "provider_error",
            "minute_bar_missing_reason": "provider_error",
            "minute_bar_notes": "provider_attempted=akshare,eastmoney_direct; akshare_status=provider_error; akshare_reason=provider_error; eastmoney_status=provider_error; eastmoney_reason=provider_error",
        }
    )
    yfinance_minute_record = _minute_record("515880.SH").model_copy(
        update={
            "minute_bar_provider": "yfinance",
            "minute_bar_status": "available",
            "minute_bars_available": True,
            "minute_bar_count": 1,
            "minute_bar_notes": "provider_attempted=akshare,eastmoney_direct,yfinance; provider_success=yfinance; yfinance_status=available; yfinance_ticker=515880.SS; yfinance_reason=",
        }
    )

    report = build_provider_health_report([yfinance_record, eastmoney_record, akshare_minute_record, yfinance_minute_record])
    eastmoney_section = report.split("## Eastmoney Direct", 1)[1].split("## Manual", 1)[0]
    yfinance_section = report.split("## YFinance", 1)[1].split("## Eastmoney Direct", 1)[0]
    akshare_minute_section = report.split("## AKShare Minute Bars", 1)[1].split("## AKShare A", 1)[0]

    assert "yfinance.Ticker" not in eastmoney_section
    assert "eastmoney_direct.stock_get" in eastmoney_section
    assert "yfinance.Ticker" in yfinance_section
    assert "yfinance.history" in yfinance_section
    assert "fund_etf_hist_min_em" in akshare_minute_section


def test_minute_probe_disabled_preserves_strict_result(tmp_path):
    without_probe = run_pipeline(output_dir=tmp_path / "without", provider_mode="mock", profile="tech", strict=True)
    with_probe = run_pipeline(
        output_dir=tmp_path / "with",
        provider_mode="mock",
        profile="tech",
        strict=True,
        include_minute_bars=True,
    )

    assert without_probe.exit_code == with_probe.exit_code
    assert not (tmp_path / "without" / "minute_bars_snapshot.csv").exists()
    assert (tmp_path / "with" / "minute_bars_snapshot.csv").exists()


def test_manual_gold_minute_bars_are_not_supported(tmp_path):
    output_dir = tmp_path / "gold"
    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", include_minute_bars=True)
    snapshot = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")
    gold = snapshot[snapshot["symbol"] == "GOLD_CNY"].iloc[0]

    assert gold["minute_bar_status"] == "not_supported"
    assert gold["minute_bar_missing_reason"] == "manual_price_only"


def test_minute_probe_script_and_docs_are_present():
    script = Path("scripts/run_tech_minute_probe.ps1").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    output_contract = Path("docs/output_contract.md").read_text(encoding="utf-8")
    matrix = Path("docs/api_field_capability_matrix.md").read_text(encoding="utf-8")
    known_issues = Path("docs/known_issues.md").read_text(encoding="utf-8")

    assert "--include-minute-bars" in script
    assert "outputs_tech_minute_probe_latest" in script
    assert "Minute Bars Ingestion Probe" in readme
    assert "Minute Bars Probe Contract" in output_contract
    assert "v0.7.2a probe introduced" in matrix
    assert "Minute bars probe introduced in v0.7.2a" in known_issues
