from datetime import datetime, timedelta, timezone

from market_price_guard.freshness import assess_freshness
from market_price_guard.models import RawPrice


RULES = {
    "default": {"max_age_seconds_open": 60, "max_age_seconds_closed": 86400},
    "manual": {"max_age_seconds": 3600},
    "markets": {"CN": {"max_age_seconds_open": 60, "max_age_seconds_closed": 86400}},
}


def test_open_market_price_over_max_age_is_stale():
    now = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
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
    assert "不可用于盘中做T" in reason


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
