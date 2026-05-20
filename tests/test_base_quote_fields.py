from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from market_price_guard.main import run_pipeline
from market_price_guard.models import Instrument, RawPrice, WatchProject, Watchlist
from market_price_guard.normalize import load_yaml, normalize_records
from market_price_guard.providers.akshare_provider import AkshareProvider
from market_price_guard.providers.eastmoney_direct_provider import EastmoneyDirectProvider
from market_price_guard.providers.yfinance_provider import YFinanceProvider
from market_price_guard.report import build_completeness_report, build_debug_bundle, build_upload_bundle, get_blocking_records


RULES = load_yaml(Path("config/stale_rules.yaml"))
NOW = datetime(2026, 5, 18, 7, 10, tzinfo=timezone.utc)


def test_base_quote_calculation_and_completeness_complete():
    record = _normalize_one(
        RawPrice(
            symbol="159819.SZ",
            price=10.5,
            currency="CNY",
            source="akshare",
            quote_time=NOW,
            fetch_time=NOW,
            market_status="closed",
            prev_close=10.0,
            open_price=10.1,
            high_price=10.8,
            low_price=9.9,
            volume=1000,
            amount=10500,
        )
    )

    assert record.last_price == 10.5
    assert record.price_change == 0.5
    assert record.price_change_pct == 5.0
    assert record.amplitude_pct == 9.0
    assert record.price_change_source == "calculated_from_last_and_prev_close"
    assert record.price_change_pct_source == "calculated_from_last_and_prev_close"
    assert record.amplitude_pct_source == "calculated_from_high_low_prev_close"
    assert record.base_quote_completeness == "complete"
    assert record.base_quote_fields_available_count == 7


def test_base_quote_completeness_partial_price_only_and_missing():
    partial = _normalize_one(
        RawPrice(
            symbol="159819.SZ",
            price=10,
            currency="CNY",
            source="akshare",
            quote_time=NOW,
            fetch_time=NOW,
            market_status="closed",
            prev_close=9,
            open_price=9.5,
            high_price=10.2,
        )
    )
    price_only = _normalize_one(RawPrice(symbol="159819.SZ", price=10, currency="CNY", source="manual", quote_time=NOW, fetch_time=NOW, market_status="closed"))
    missing = _normalize_one(RawPrice(symbol="159819.SZ", price=None, currency="CNY", source="mock", quote_time=NOW, fetch_time=NOW, market_status="closed"))

    assert partial.base_quote_completeness == "partial"
    assert price_only.base_quote_completeness == "price_only"
    assert missing.base_quote_completeness == "missing"


def test_prev_close_zero_does_not_divide_by_zero():
    record = _normalize_one(
        RawPrice(
            symbol="159819.SZ",
            price=10,
            currency="CNY",
            source="akshare",
            quote_time=NOW,
            fetch_time=NOW,
            market_status="closed",
            prev_close=0,
            high_price=11,
            low_price=9,
        )
    )

    assert record.price_change_pct is None
    assert record.amplitude_pct is None
    assert "price_change_pct_prev_close_not_positive" in record.base_quote_field_errors


def test_exchange_country_market_and_calendar_do_not_change_market():
    cases = [
        ("159819.SZ", "CN", "SZ", "CN", "CN_A_SHARE"),
        ("513300.SH", "CN", "SH", "CN", "CN_A_SHARE"),
        ("00883.HK", "HK", "HK", "HK", "HK"),
        ("GOLD_CNY", "MANUAL", "MANUAL", "MANUAL", "MANUAL"),
    ]
    for symbol, market, exchange, country, calendar in cases:
        record = _normalize_one(
            RawPrice(symbol=symbol, price=1, currency="CNY", source="mock", quote_time=NOW, fetch_time=NOW, market_status="closed"),
            symbol=symbol,
            market=market,
        )
        assert record.market == market
        assert record.exchange == exchange
        assert record.country_market == country
        assert record.trading_calendar == calendar


def test_base_quote_missing_does_not_create_strict_blocker():
    record = _normalize_one(
        RawPrice(symbol="159819.SZ", price=10, currency="CNY", source="akshare", quote_time=NOW, fetch_time=NOW, market_status="closed"),
        required_for_operation=True,
    )

    assert record.base_quote_completeness == "price_only"
    assert get_blocking_records([record]) == []


def test_eastmoney_base_fields_mapping_and_trust_unchanged():
    payload = {
        "rc": 0,
        "data": {
            "f43": 10.5,
            "f57": "159819",
            "f58": "AI ETF",
            "f86": 1779087600,
            "f60": 10,
            "f46": 10.1,
            "f44": 10.8,
            "f45": 9.9,
            "f47": 1000,
            "f48": 10500,
            "f169": 0.5,
            "f170": 5,
        },
    }
    raw = EastmoneyDirectProvider(http_get=lambda url, params, timeout: payload).fetch(["159819.SZ"])["159819.SZ"]
    record = _normalize_one(raw)

    assert record.prev_close == 10
    assert record.open_price == 10.1
    assert record.high_price == 10.8
    assert record.low_price == 9.9
    assert record.volume == 1000
    assert record.amount == 10500
    assert record.price_change == 0.5
    assert record.price_change_pct == 5
    assert record.quote_trust_tier == "reference"
    assert record.usable_for_operation is False


def test_akshare_base_fields_mapping_from_dataframe():
    class FakeAk:
        @staticmethod
        def fund_etf_spot_em():
            return pd.DataFrame(
                [
                    {
                        "代码": "159819",
                        "名称": "AI ETF",
                        "最新价": 10.5,
                        "昨收": 10,
                        "今开": 10.1,
                        "最高": 10.8,
                        "最低": 9.9,
                        "成交量": 1000,
                        "成交额": 10500,
                        "涨跌额": 0.5,
                        "涨跌幅": 5,
                        "更新时间": "2026-05-18 15:01:00+08:00",
                    }
                ]
            )

    raw = AkshareProvider(ak_module=FakeAk()).fetch(["159819.SZ"])["159819.SZ"]
    record = _normalize_one(raw)

    assert record.prev_close == 10
    assert record.open_price == 10.1
    assert record.high_price == 10.8
    assert record.low_price == 9.9
    assert record.volume == 1000
    assert record.amount == 10500
    assert record.price_change == 0.5
    assert record.price_change_pct == 5


def test_yfinance_base_fields_mapping_from_fast_info():
    class FakeTicker:
        fast_info = {
            "last_price": 10.5,
            "currency": "CNY",
            "last_trade_time": NOW,
            "previous_close": 10,
            "open": 10.1,
            "day_high": 10.8,
            "day_low": 9.9,
            "last_volume": 1000,
        }

        def history(self, period, interval):
            return pd.DataFrame()

    class FakeYF:
        @staticmethod
        def Ticker(symbol):
            return FakeTicker()

    raw = YFinanceProvider(yf_module=FakeYF()).fetch(["159819.SZ"])["159819.SZ"]
    record = _normalize_one(raw)

    assert record.prev_close == 10
    assert record.open_price == 10.1
    assert record.high_price == 10.8
    assert record.low_price == 9.9
    assert record.volume == 1000
    assert record.price_change_pct == 5.0


def test_outputs_include_base_quote_columns_and_reports(tmp_path):
    output_dir = tmp_path / "out"
    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)
    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")

    for column in [
        "last_price",
        "prev_close",
        "open_price",
        "high_price",
        "low_price",
        "volume",
        "amount",
        "price_change",
        "price_change_pct",
        "amplitude_pct",
        "base_quote_completeness",
        "base_quote_missing_fields",
        "exchange",
        "country_market",
        "trading_calendar",
    ]:
        assert column in df.columns
    assert "base_quote_completeness" in (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    assert "Base Quote Fields Summary" in (output_dir / "debug_bundle.md").read_text(encoding="utf-8")
    assert "Base quote completeness summary" in (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")


def test_watchlist_and_scan_reports_include_base_quote_completeness(tmp_path):
    watchlist_dir = tmp_path / "watchlist"
    scan_dir = tmp_path / "scan"
    run_pipeline(output_dir=watchlist_dir, provider_mode="mock", profile="tech", universe="tech_watchlist", quote_purpose="reference")
    run_pipeline(output_dir=scan_dir, provider_mode="mock", profile="tech", universe="tech_scan_ai", quote_purpose="reference")

    assert "base_quote_completeness" in (watchlist_dir / "candidate_watchlist_report.md").read_text(encoding="utf-8")
    assert "base_quote_completeness" in (scan_dir / "scan_universe_report.md").read_text(encoding="utf-8")


def test_base_quote_docs_are_updated():
    output_contract = Path("docs/output_contract.md").read_text(encoding="utf-8")
    matrix = Path("docs/api_field_capability_matrix.md").read_text(encoding="utf-8")
    known_issues = Path("docs/known_issues.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "Base Quote Fields Contract" in output_contract
    assert "v0.7.1.4 standardized base quote fields" in matrix
    assert "exchange/country_market/trading_calendar" in known_issues
    assert "Base Quote Field Normalization" in readme


def _normalize_one(raw: RawPrice, symbol: str = "159819.SZ", market: str = "CN", required_for_operation: bool = False):
    watchlist = Watchlist(
        projects={
            "tech": WatchProject(
                display_name="tech",
                allow_full_detail=True,
                instruments=[
                    Instrument(
                        symbol=symbol,
                        name=symbol,
                        market=market,
                        provider="mock",
                        required_for_operation=required_for_operation,
                        asset_role="ai_tech_equity",
                    )
                ],
            )
        }
    )
    return normalize_records(watchlist, {symbol: raw}, RULES, now=NOW)[0]
