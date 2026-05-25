from datetime import datetime, timedelta, timezone

from market_price_guard.freshness import assess_freshness, market_status_for_now
from market_price_guard.models import RawPrice


RULES = {
    "default": {"max_age_seconds_open": 60, "max_age_seconds_closed": 86400, "closed_market_allowed": True},
    "manual": {"max_age_seconds": 3600},
    "markets": {"CN": {"max_age_seconds_open": 60, "max_age_seconds_closed": 86400, "closed_market_allowed": True}},
}


def test_open_market_price_over_max_age_is_stale():
    now = datetime(2026, 5, 18, 14, 0, tzinfo=timezone(timedelta(hours=8)))
    raw = RawPrice(
        symbol="601985.SH",
        price=10.0,
        currency="CNY",
        source="mock",
        quote_time=now - timedelta(seconds=61),
        fetch_time=now,
        market_status="open",
    )

    is_stale, reason = assess_freshness(raw, "CN", RULES, now=now)

    assert is_stale is True
    assert "不可用于具体操作建议" in reason


def test_closed_market_price_is_reference_not_intraday_t():
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    raw = RawPrice(
        symbol="601985.SH",
        price=10.0,
        currency="CNY",
        source="mock",
        quote_time=now - timedelta(hours=1),
        fetch_time=now,
        market_status="closed",
    )

    is_stale, reason = assess_freshness(raw, "CN", RULES, now=now)

    assert is_stale is False
    assert "不适合盘中做T判断" in reason
    assert "市场已收盘" in reason


def test_closed_market_allowed_does_not_use_trading_max_age():
    quote_time = datetime(2026, 5, 18, 15, 34, 3, tzinfo=timezone(timedelta(hours=8)))
    now = datetime(2026, 5, 18, 8, 0, tzinfo=timezone.utc)
    raw = RawPrice(
        symbol="159632.SZ",
        price=1.0,
        currency="CNY",
        source="akshare",
        quote_time=quote_time,
        fetch_time=now,
        market_status="closed",
    )

    is_stale, reason = assess_freshness(raw, "CN", RULES, now=now)

    assert is_stale is False
    assert "交易中价格超过 max_age_seconds" not in reason
    assert "收盘前/最后更新时间参考" in reason


def test_closed_market_not_allowed_uses_closed_reason():
    quote_time = datetime(2026, 5, 18, 15, 34, 3, tzinfo=timezone(timedelta(hours=8)))
    now = datetime(2026, 5, 18, 8, 0, tzinfo=timezone.utc)
    rules = {
        **RULES,
        "markets": {"CN": {"max_age_seconds_open": 60, "max_age_seconds_closed": 86400, "closed_market_allowed": False}},
    }
    raw = RawPrice(
        symbol="159632.SZ",
        price=1.0,
        currency="CNY",
        source="akshare",
        quote_time=quote_time,
        fetch_time=now,
        market_status="closed",
    )

    is_stale, reason = assess_freshness(raw, "CN", rules, now=now)

    assert is_stale is True
    assert "closed_market_not_allowed" in reason
    assert "交易中价格超过 max_age_seconds" not in reason


def test_missing_quote_time_is_stale():
    raw = RawPrice(symbol="IXIC", price=100.0, currency="USD", source="mock", market_status="open")

    is_stale, reason = assess_freshness(raw, "US", RULES)

    assert is_stale is True
    assert "quote_time 缺失" in reason


def test_manual_price_uses_entry_time():
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    raw = RawPrice(
        symbol="GOLD_CNY",
        price=775.5,
        currency="CNY",
        source="manual",
        quote_time=now,
        fetch_time=now,
        entry_time=now - timedelta(hours=2),
        market_status="manual",
    )

    is_stale, reason = assess_freshness(raw, "MANUAL", RULES, now=now)

    assert is_stale is True
    assert "manual 价格超过允许录入时间" in reason


def test_cn_after_close_uses_now_market_time_for_sh_not_quote_time():
    now = datetime(2026, 5, 18, 15, 10, tzinfo=timezone(timedelta(hours=8)))
    quote_time = datetime(2026, 5, 18, 14, 57, tzinfo=timezone(timedelta(hours=8)))
    raw = RawPrice(
        symbol="601899.SH",
        price=18.42,
        currency="CNY",
        source="yfinance",
        quote_time=quote_time,
        fetch_time=now,
        market_status="open",
    )

    is_stale, reason = assess_freshness(raw, "CN", RULES, now=now)

    assert market_status_for_now(raw, "CN", now) == "closed"
    assert is_stale is False
    assert "交易中价格超过 max_age_seconds" not in reason
    assert "市场已收盘" in reason
    assert "不适合盘中做T判断" in reason


def test_cn_after_close_uses_now_market_time_for_sz_not_quote_time():
    now = datetime(2026, 5, 18, 15, 10, tzinfo=timezone(timedelta(hours=8)))
    quote_time = datetime(2026, 5, 18, 14, 59, tzinfo=timezone(timedelta(hours=8)))
    raw = RawPrice(
        symbol="003816.SZ",
        price=4.27,
        currency="CNY",
        source="yfinance",
        quote_time=quote_time,
        fetch_time=now,
        market_status="open",
    )

    is_stale, reason = assess_freshness(raw, "CN", RULES, now=now)

    assert market_status_for_now(raw, "CN", now) == "closed"
    assert is_stale is False
    assert "交易中价格超过 max_age_seconds" not in reason


def test_cn_trading_now_still_uses_trading_max_age_for_sh():
    now = datetime(2026, 5, 18, 14, 58, tzinfo=timezone(timedelta(hours=8)))
    quote_time = datetime(2026, 5, 18, 14, 50, tzinfo=timezone(timedelta(hours=8)))
    raw = RawPrice(
        symbol="601899.SH",
        price=18.42,
        currency="CNY",
        source="yfinance",
        quote_time=quote_time,
        fetch_time=now,
        market_status="closed",
    )

    is_stale, reason = assess_freshness(raw, "CN", RULES, now=now)

    assert market_status_for_now(raw, "CN", now) == "open"
    assert is_stale is True
    assert "交易中价格超过 max_age_seconds" in reason


def test_cn_trading_now_still_uses_trading_max_age_for_sz():
    now = datetime(2026, 5, 18, 14, 58, tzinfo=timezone(timedelta(hours=8)))
    quote_time = datetime(2026, 5, 18, 14, 50, tzinfo=timezone(timedelta(hours=8)))
    raw = RawPrice(
        symbol="003816.SZ",
        price=4.27,
        currency="CNY",
        source="yfinance",
        quote_time=quote_time,
        fetch_time=now,
        market_status="closed",
    )

    is_stale, reason = assess_freshness(raw, "CN", RULES, now=now)

    assert market_status_for_now(raw, "CN", now) == "open"
    assert is_stale is True
    assert "交易中价格超过 max_age_seconds" in reason


def test_small_future_quote_time_within_tolerance_is_not_stale():
    now = datetime(2026, 5, 22, 9, 38, 0, tzinfo=timezone(timedelta(hours=8)))
    raw = RawPrice(
        symbol="688256.SH",
        price=129.0,
        currency="CNY",
        source="eastmoney_direct",
        quote_time=now + timedelta(seconds=19),
        fetch_time=now,
        market_status="open",
    )

    is_stale, reason = assess_freshness(raw, "CN", RULES, now=now)

    assert is_stale is False
    assert "future_quote_time" not in reason


def test_large_future_quote_time_over_tolerance_is_stale():
    now = datetime(2026, 5, 22, 9, 38, 0, tzinfo=timezone(timedelta(hours=8)))
    raw = RawPrice(
        symbol="688256.SH",
        price=129.0,
        currency="CNY",
        source="eastmoney_direct",
        quote_time=now + timedelta(seconds=121),
        fetch_time=now,
        market_status="open",
    )

    is_stale, reason = assess_freshness(raw, "CN", RULES, now=now)

    assert is_stale is True
    assert "future_quote_time" in reason
