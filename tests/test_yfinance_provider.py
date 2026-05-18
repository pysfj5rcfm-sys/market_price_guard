from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd

from market_price_guard.models import PriceRecord, RawPrice
from market_price_guard.normalize import normalize_records
from market_price_guard.provider_router import RouterConfig, route_symbol
from market_price_guard.models import Instrument, Watchlist, WatchProject
from market_price_guard.providers.yfinance_provider import YFinanceProvider, yahoo_ticker_for_symbol
from market_price_guard.report import build_completeness_report, build_provider_health_report, get_blocking_records


def test_00883_maps_to_yahoo_0883():
    assert yahoo_ticker_for_symbol("00883.HK") == "0883.HK"
    assert yahoo_ticker_for_symbol("883.HK") == "0883.HK"


def test_a_share_symbols_map_to_yahoo_tickers():
    assert yahoo_ticker_for_symbol("601899.SH") == "601899.SS"
    assert yahoo_ticker_for_symbol("601985.SH") == "601985.SS"
    assert yahoo_ticker_for_symbol("003816.SZ") == "003816.SZ"


def test_yfinance_provider_reads_fast_info_price_currency_and_time():
    yf = _yf(
        fast_info={
            "last_price": 21.35,
            "currency": "HKD",
            "last_trade_time": datetime(2026, 5, 18, 16, 5, tzinfo=timezone.utc),
        }
    )

    raw = YFinanceProvider(yf).fetch(["00883.HK"])["00883.HK"]

    assert raw.price == 21.35
    assert raw.currency == "HKD"
    assert raw.source == "yfinance"
    assert raw.quote_time == datetime(2026, 5, 18, 16, 5, tzinfo=timezone.utc)
    assert raw.provider_diagnostics["yahoo_ticker"] == "0883.HK"


def test_yfinance_provider_reads_a_share_fast_info_price_currency_and_time():
    yf = _yf(
        fast_info={
            "last_price": 18.42,
            "currency": "CNY",
            "last_trade_time": datetime(2026, 5, 18, 7, 5, tzinfo=timezone.utc),
        }
    )

    raw = YFinanceProvider(yf).fetch(["601899.SH"])["601899.SH"]

    assert raw.price == 18.42
    assert raw.currency == "CNY"
    assert raw.source == "yfinance"
    assert raw.market == "CN"
    assert raw.market_status == "closed"
    assert raw.provider_diagnostics["yahoo_ticker"] == "601899.SS"
    assert raw.provider_diagnostics["category"] == "A_SHARE"


def test_yfinance_provider_reads_history_close_and_quote_time():
    index = pd.DatetimeIndex([pd.Timestamp("2026-05-18 15:59:00", tz="Asia/Hong_Kong")])
    history = pd.DataFrame({"Close": [21.35]}, index=index)

    raw = YFinanceProvider(_yf(history_1m=history)).fetch(["00883.HK"])["00883.HK"]

    assert raw.price == 21.35
    assert raw.quote_time is not None
    assert raw.quote_time.isoformat() == "2026-05-18T15:59:00+08:00"
    assert "quote_time_missing" not in raw.quality_issues


def test_yfinance_provider_reads_a_share_history_close_and_quote_time():
    index = pd.DatetimeIndex([pd.Timestamp("2026-05-18 14:59:00", tz="Asia/Shanghai")])
    history = pd.DataFrame({"Close": [10.91]}, index=index)

    raw = YFinanceProvider(_yf(history_1m=history)).fetch(["601985.SH"])["601985.SH"]

    assert raw.price == 10.91
    assert raw.quote_time is not None
    assert raw.quote_time.isoformat() == "2026-05-18T14:59:00+08:00"
    assert raw.market_status == "open"


def test_yfinance_daily_history_marks_low_precision():
    index = pd.DatetimeIndex([pd.Timestamp("2026-05-18", tz="Asia/Hong_Kong")])
    history = pd.DataFrame({"Close": [21.35]}, index=index)

    raw = YFinanceProvider(_yf(history_1d=history)).fetch(["00883.HK"])["00883.HK"]

    assert raw.price == 21.35
    assert "daily_close_only" in raw.quality_issues
    assert "low_precision_quote_time" in raw.quality_issues


def test_yfinance_provider_invalid_price():
    yf = _yf(fast_info={"last_price": 0, "currency": "HKD", "last_trade_time": datetime(2026, 5, 18, 16, 5, tzinfo=timezone.utc)})

    raw = YFinanceProvider(yf).fetch(["00883.HK"])["00883.HK"]

    assert raw.price is None
    assert "invalid_price" in raw.quality_issues


def test_yfinance_provider_a_share_invalid_price():
    yf = _yf(fast_info={"last_price": 0, "currency": "CNY", "last_trade_time": datetime(2026, 5, 18, 7, 5, tzinfo=timezone.utc)})

    raw = YFinanceProvider(yf).fetch(["601899.SH"])["601899.SH"]

    assert raw.price is None
    assert "invalid_price" in raw.quality_issues


def test_yfinance_provider_quote_time_missing():
    yf = _yf(fast_info={"last_price": 21.35, "currency": "HKD"})

    raw = YFinanceProvider(yf).fetch(["00883.HK"])["00883.HK"]

    assert raw.quote_time is None
    assert "quote_time_missing" in raw.quality_issues


def test_yfinance_provider_a_share_quote_time_missing():
    yf = _yf(fast_info={"last_price": 18.42, "currency": "CNY"})

    raw = YFinanceProvider(yf).fetch(["601899.SH"])["601899.SH"]

    assert raw.quote_time is None
    assert "quote_time_missing" in raw.quality_issues


def test_yfinance_provider_assumes_hkd_when_currency_missing():
    yf = _yf(fast_info={"last_price": 21.35, "last_trade_time": datetime(2026, 5, 18, 16, 5, tzinfo=timezone.utc)})

    raw = YFinanceProvider(yf).fetch(["00883.HK"])["00883.HK"]

    assert raw.currency == "HKD"
    assert "assumed_currency_hkd" in raw.quality_issues


def test_yfinance_provider_a_share_assumes_cny_when_currency_missing():
    yf = _yf(fast_info={"last_price": 18.42, "last_trade_time": datetime(2026, 5, 18, 7, 5, tzinfo=timezone.utc)})

    raw = YFinanceProvider(yf).fetch(["601899.SH"])["601899.SH"]

    assert raw.currency == "CNY"
    assert "assumed_currency_cny" in raw.quality_issues


def test_yfinance_does_not_handle_gold_or_etf():
    prices = YFinanceProvider(_yf()).fetch(["GOLD_CNY", "159819.SZ", "510300.SH", "IXIC", "USD_CNY", "HKD_CNY"])

    assert prices == {}


def test_a_share_quote_time_uses_shanghai_status_and_utc_age():
    quote_time = datetime(2026, 5, 18, 7, 5, tzinfo=timezone.utc)
    raw = YFinanceProvider(_yf(fast_info={"last_price": 18.42, "currency": "CNY", "last_trade_time": quote_time})).fetch(["601899.SH"])[
        "601899.SH"
    ]
    watchlist = Watchlist(
        projects={
            "energy": WatchProject(
                display_name="energy",
                allow_full_detail=True,
                instruments=[Instrument(symbol="601899.SH", name="紫金矿业A", market="CN", provider="yfinance", required_for_operation=True)],
            )
        }
    )
    records = normalize_records(
        watchlist,
        {"601899.SH": raw},
        {"default": {"max_age_seconds_open": 900, "max_age_seconds_closed": 86400}, "markets": {"CN": {"max_age_seconds_open": 900, "max_age_seconds_closed": 86400}}},
        now=datetime(2026, 5, 18, 7, 10, tzinfo=timezone.utc),
    )

    assert records[0].provider_diagnostics["age_seconds"] == 300
    assert records[0].market_status == "closed"
    assert records[0].is_stale is False


def test_hk_quote_time_uses_hong_kong_status_and_utc_age():
    quote_time = datetime(2026, 5, 18, 16, 5, tzinfo=timezone.utc)
    raw = YFinanceProvider(_yf(fast_info={"last_price": 21.35, "currency": "HKD", "last_trade_time": quote_time})).fetch(["00883.HK"])[
        "00883.HK"
    ]
    watchlist = Watchlist(
        projects={
            "energy": WatchProject(
                display_name="energy",
                allow_full_detail=True,
                instruments=[Instrument(symbol="00883.HK", name="中海油H", market="HK", provider="yfinance", required_for_operation=True)],
            )
        }
    )
    records = normalize_records(
        watchlist,
        {"00883.HK": raw},
        {"default": {"max_age_seconds_open": 900, "max_age_seconds_closed": 86400}, "markets": {"HK": {"max_age_seconds_open": 900, "max_age_seconds_closed": 86400}}},
        now=datetime(2026, 5, 18, 16, 10, tzinfo=timezone.utc),
    )

    assert records[0].provider_diagnostics["age_seconds"] == 300
    assert records[0].market_status == "closed"
    assert records[0].is_stale is False


def test_akshare_failed_yfinance_success_selected_and_not_blocking():
    raw = route_symbol(
        _instrument(),
        {
            "akshare": _provider(_raw("00883.HK", "akshare", None, ["provider_error"])),
            "yfinance": _provider(_raw("00883.HK", "yfinance", 21.35)),
            "mock": _provider(_raw("00883.HK", "mock", 21.0)),
        },
        RouterConfig(provider_mode="live"),
    )
    record = _record(raw, required=True)

    assert raw.provider_diagnostics["selected_provider"] == "yfinance"
    assert raw.provider_diagnostics["fallback_used"] is True
    assert get_blocking_records([record]) == []


def test_a_share_akshare_failed_yfinance_success_selected(symbol="601899.SH"):
    raw = route_symbol(
        _instrument(symbol=symbol, market="CN"),
        {
            "akshare": _provider(_raw(symbol, "akshare", None, ["provider_error"], currency="CNY")),
            "yfinance": _provider(_raw(symbol, "yfinance", 18.42, currency="CNY")),
            "mock": _provider(_raw(symbol, "mock", 18.0, currency="CNY")),
        },
        RouterConfig(provider_mode="live"),
    )
    record = _record(raw, required=True, market="CN")

    assert raw.provider_diagnostics["selected_provider"] == "yfinance"
    assert raw.provider_diagnostics["fallback_used"] is True
    assert get_blocking_records([record]) == []


def test_601985_akshare_failed_yfinance_success_selected():
    test_a_share_akshare_failed_yfinance_success_selected("601985.SH")


def test_003816_akshare_failed_yfinance_success_selected():
    test_a_share_akshare_failed_yfinance_success_selected("003816.SZ")


def test_yfinance_failed_continues_to_mock_fallback_not_usable():
    raw = route_symbol(
        _instrument(),
        {
            "akshare": _provider(_raw("00883.HK", "akshare", None, ["provider_error"])),
            "yfinance": _provider(_raw("00883.HK", "yfinance", None, ["provider_error"])),
            "mock": _provider(_raw("00883.HK", "mock", 21.0)),
        },
        RouterConfig(provider_mode="live"),
    )

    assert raw.source == "mock_fallback"
    assert "mock_fallback_not_allowed" in raw.quality_issues


def test_a_share_yfinance_failed_continues_to_mock_fallback_not_usable():
    raw = route_symbol(
        _instrument(symbol="601899.SH", market="CN"),
        {
            "akshare": _provider(_raw("601899.SH", "akshare", None, ["provider_error"], currency="CNY")),
            "yfinance": _provider(_raw("601899.SH", "yfinance", None, ["provider_error"], currency="CNY")),
            "mock": _provider(_raw("601899.SH", "mock", 18.0, currency="CNY")),
        },
        RouterConfig(provider_mode="live"),
    )

    assert raw.source == "mock_fallback"
    assert "mock_fallback_not_allowed" in raw.quality_issues


def test_provider_reports_show_yfinance_secondary_success():
    raw = route_symbol(
        _instrument(),
        {
            "akshare": _provider(_raw("00883.HK", "akshare", None, ["provider_error"])),
            "yfinance": _provider(_raw("00883.HK", "yfinance", 21.35)),
        },
        RouterConfig(provider_mode="live"),
    )
    record = _record(raw, required=True)

    health = build_provider_health_report([record], provider_mode="live")
    completeness = build_completeness_report([record])

    assert "provider=akshare" in health
    assert "provider=yfinance" in health
    assert "selected_provider: yfinance" in health
    assert "fallback_used: True" in health
    assert "使用 yfinance secondary provider" in completeness
    assert "research/educational use" in completeness


def test_provider_reports_show_a_share_yfinance_secondary_success():
    raw = route_symbol(
        _instrument(symbol="601899.SH", market="CN"),
        {
            "akshare": _provider(_raw("601899.SH", "akshare", None, ["provider_error"], currency="CNY")),
            "yfinance": _provider(_raw("601899.SH", "yfinance", 18.42, currency="CNY")),
        },
        RouterConfig(provider_mode="live"),
    )
    record = _record(raw, required=True, market="CN")

    health = build_provider_health_report([record], provider_mode="live")
    completeness = build_completeness_report([record])

    assert "601899.SH" in health
    assert "provider=akshare" in health
    assert "provider=yfinance" in health
    assert "selected_provider: yfinance" in health
    assert "使用 yfinance secondary provider" in completeness
    assert "research/educational use" in completeness


def _yf(fast_info=None, history_1m=None, history_1d=None):
    class Ticker:
        def __init__(self, ticker):
            self.ticker = ticker
            self.fast_info = fast_info or {}

        def history(self, period, interval):
            if period == "1d" and interval == "1m":
                return history_1m if history_1m is not None else pd.DataFrame()
            if period == "5d" and interval == "1d":
                return history_1d if history_1d is not None else pd.DataFrame()
            return pd.DataFrame()

    return SimpleNamespace(Ticker=Ticker)


def _provider(raw):
    return SimpleNamespace(fetch=lambda symbols: {raw.symbol: raw})


def _instrument(symbol="00883.HK", market="HK"):
    return Instrument(
        symbol=symbol,
        name=symbol,
        market=market,
        provider="akshare",
        provider_priority=["akshare", "yfinance", "mock"],
        required_for_operation=True,
    )


def _raw(symbol, source, price, quality_issues=None, currency="HKD"):
    now = datetime(2026, 5, 18, 16, 5, tzinfo=timezone.utc)
    return RawPrice(
        symbol=symbol,
        price=price,
        currency=currency,
        source=source,
        quote_time=now if price is not None else None,
        fetch_time=now,
        market_status="closed",
        quality_issues=quality_issues or [],
    )


def _record(raw, required=False, market="HK"):
    return PriceRecord(
        project="energy",
        symbol=raw.symbol,
        name=raw.symbol,
        market=market,
        price=raw.price,
        currency=raw.currency,
        source=raw.source,
        quote_time=raw.quote_time,
        fetch_time=raw.fetch_time,
        market_status=raw.market_status,
        is_stale=bool(raw.quality_issues),
        stale_reason=", ".join(raw.quality_issues),
        required_for_operation=required,
        quality_issues=raw.quality_issues,
        provider_diagnostics=raw.provider_diagnostics,
    )
