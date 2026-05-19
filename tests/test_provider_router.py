from __future__ import annotations

from datetime import datetime, timezone

from market_price_guard.models import Instrument, PriceRecord, RawPrice, Watchlist, WatchProject
from market_price_guard.normalize import normalize_records
from market_price_guard.provider_router import RouterConfig, collect_routed_prices, route_symbol
from market_price_guard.report import build_completeness_report, build_provider_health_report, get_blocking_records, build_tech_block


class StaticProvider:
    def __init__(self, raw: RawPrice | None = None, exc: Exception | None = None):
        self.raw = raw
        self.exc = exc
        self.called = False

    def fetch(self, symbols: list[str]) -> dict[str, RawPrice]:
        self.called = True
        if self.exc:
            raise self.exc
        if self.raw is None:
            return {}
        return {self.raw.symbol: self.raw}


def test_provider_priority_only_akshare_matches_live_path():
    raw = _raw("601899.SH", "akshare", 18.42)
    instrument = _instrument("601899.SH", provider_priority=["akshare"])

    selected = route_symbol(instrument, {"akshare": StaticProvider(raw)}, RouterConfig(provider_mode="live", provider_policy="conservative"))

    assert selected.source == "akshare"
    assert selected.provider_diagnostics["selected_provider"] == "akshare"
    assert selected.provider_diagnostics["fallback_used"] is False


def test_fast_policy_a_share_effective_chain_yfinance_first():
    raw = route_symbol(
        _instrument("601899.SH", provider_priority=["akshare", "yfinance", "mock"]),
        {"yfinance": StaticProvider(_raw("601899.SH", "yfinance", 18.42)), "akshare": StaticProvider(_raw("601899.SH", "akshare", 18.0))},
        RouterConfig(provider_mode="live", provider_policy="fast"),
    )

    assert raw.provider_diagnostics["effective_provider_chain"] == ["yfinance", "akshare", "mock"]
    assert raw.provider_diagnostics["selected_provider"] == "yfinance"
    assert any(attempt["provider"] == "akshare" and attempt["status"] == "skipped" for attempt in raw.provider_diagnostics["provider_attempts"])


def test_fast_policy_hk_effective_chain_yfinance_first():
    raw = route_symbol(
        _instrument("00883.HK", provider_priority=["akshare", "yfinance", "mock"], market="HK"),
        {"yfinance": StaticProvider(_raw("00883.HK", "yfinance", 21.35)), "akshare": StaticProvider(_raw("00883.HK", "akshare", 21.0))},
        RouterConfig(provider_mode="live", provider_policy="fast"),
    )

    assert raw.provider_diagnostics["effective_provider_chain"] == ["yfinance", "akshare", "mock"]
    assert raw.provider_diagnostics["selected_provider"] == "yfinance"


def test_fast_policy_etf_keeps_akshare_first():
    raw = route_symbol(
        _instrument("159819.SZ", provider_priority=["akshare", "mock"]),
        {"akshare": StaticProvider(_raw("159819.SZ", "akshare", 0.921)), "yfinance": StaticProvider(exc=AssertionError("no yfinance"))},
        RouterConfig(provider_mode="live", provider_policy="fast"),
    )

    assert raw.provider_diagnostics["effective_provider_chain"] == ["akshare", "mock"]
    assert raw.provider_diagnostics["selected_provider"] == "akshare"


def test_reference_purpose_uses_eastmoney_first_for_tech_etf():
    raw = route_symbol(
        _instrument("159819.SZ", provider_priority=["akshare", "mock"]),
        {
            "eastmoney_direct": StaticProvider(_raw("159819.SZ", "eastmoney_direct", 0.923)),
            "akshare": StaticProvider(_raw("159819.SZ", "akshare", 0.921)),
            "yfinance": StaticProvider(_raw("159819.SZ", "yfinance", 0.922)),
            "mock": StaticProvider(_raw("159819.SZ", "mock", 0.90)),
        },
        RouterConfig(provider_mode="live", provider_policy="fast", quote_purpose="reference"),
    )

    assert raw.provider_diagnostics["effective_provider_chain"] == ["eastmoney_direct", "yfinance", "akshare", "mock"]
    assert raw.provider_diagnostics["selected_provider"] == "eastmoney_direct"
    assert raw.provider_diagnostics["quote_purpose"] == "reference"
    assert any(
        attempt["reason"] == "skipped because eastmoney_direct reference quote succeeded in reference mode"
        for attempt in raw.provider_diagnostics["provider_attempts"]
        if attempt["status"] == "skipped"
    )


def test_fast_policy_gold_keeps_manual():
    raw = route_symbol(
        _instrument("GOLD_CNY", provider="manual", provider_priority=["manual"], market="MANUAL"),
        {"manual": StaticProvider(_raw("GOLD_CNY", "manual", 1040.0, market_status="manual")), "yfinance": StaticProvider(exc=AssertionError("no yfinance"))},
        RouterConfig(provider_mode="live", provider_policy="fast"),
    )

    assert raw.provider_diagnostics["effective_provider_chain"] == ["manual"]
    assert raw.provider_diagnostics["selected_provider"] == "manual"


def test_conservative_policy_stock_akshare_first_then_yfinance():
    raw = route_symbol(
        _instrument("601899.SH", provider_priority=["yfinance", "akshare", "mock"]),
        {"akshare": StaticProvider(_raw("601899.SH", "akshare", 18.42)), "yfinance": StaticProvider(_raw("601899.SH", "yfinance", 18.0))},
        RouterConfig(provider_mode="live", provider_policy="conservative"),
    )

    assert raw.provider_diagnostics["effective_provider_chain"] == ["akshare", "yfinance", "mock"]
    assert raw.provider_diagnostics["selected_provider"] == "akshare"


def test_conservative_policy_akshare_failed_then_yfinance():
    raw = route_symbol(
        _instrument("00883.HK", provider_priority=["akshare", "yfinance", "mock"], market="HK"),
        {
            "akshare": StaticProvider(_raw("00883.HK", "akshare", None, quality_issues=["provider_error"])),
            "yfinance": StaticProvider(_raw("00883.HK", "yfinance", 21.35)),
        },
        RouterConfig(provider_mode="live", provider_policy="conservative"),
    )

    assert raw.provider_diagnostics["selected_provider"] == "yfinance"
    assert raw.provider_diagnostics["fallback_used"] is True


def test_diagnostic_policy_marks_report_mode_active():
    raw = route_symbol(
        _instrument("601899.SH", provider_priority=["akshare", "yfinance", "mock"]),
        {"akshare": StaticProvider(_raw("601899.SH", "akshare", 18.42))},
        RouterConfig(provider_mode="live", provider_policy="diagnostic"),
    )
    report = build_provider_health_report([_record(raw)], provider_mode="live")

    assert "provider_policy=diagnostic" in report
    assert "diagnostic mode active" in report


def test_provider_priority_akshare_to_mock_tries_mock_after_failure():
    instrument = _instrument("601899.SH", provider_priority=["akshare", "mock"])
    providers = {
        "akshare": StaticProvider(_raw("601899.SH", "akshare", None, quality_issues=["provider_error"])),
        "mock": StaticProvider(_raw("601899.SH", "mock", 18.42)),
    }

    selected = route_symbol(instrument, providers, RouterConfig(provider_mode="live", provider_policy="diagnostic"))

    assert selected.source == "mock_fallback"
    assert selected.price == 18.42
    assert selected.provider_diagnostics["fallback_used"] is True
    assert "mock_fallback_not_allowed" in selected.quality_issues


def test_allow_mock_fallback_for_operation_makes_mock_fallback_usable():
    instrument = _instrument(
        "601899.SH",
        provider_priority=["akshare", "mock"],
        allow_mock_fallback_for_operation=True,
    )
    providers = {
        "akshare": StaticProvider(_raw("601899.SH", "akshare", None, quality_issues=["provider_error"])),
        "mock": StaticProvider(_raw("601899.SH", "mock", 18.42)),
    }

    selected = route_symbol(instrument, providers, RouterConfig(provider_mode="live", provider_policy="diagnostic"))

    assert selected.source == "mock"
    assert "mock_fallback_not_allowed" not in selected.quality_issues
    assert selected.provider_diagnostics["usable_for_operation"] is True


def test_provider_priority_akshare_to_manual_tries_manual_after_failure():
    instrument = _instrument(
        "TEST_MANUAL",
        provider_priority=["akshare", "manual"],
        allow_manual_fallback_for_operation=True,
    )
    providers = {
        "akshare": StaticProvider(_raw("TEST_MANUAL", "akshare", None, quality_issues=["provider_error"])),
        "manual": StaticProvider(_raw("TEST_MANUAL", "manual", 100.0)),
    }

    selected = route_symbol(instrument, providers, RouterConfig(provider_mode="live"))

    assert selected.source == "manual"
    assert selected.provider_diagnostics["selected_provider"] == "manual"
    assert selected.provider_diagnostics["fallback_used"] is True


def test_gold_cny_only_uses_manual_not_akshare():
    instrument = _instrument("GOLD_CNY", provider="manual", provider_priority=["manual"], market="MANUAL")
    providers = {
        "akshare": StaticProvider(exc=AssertionError("akshare should not be called")),
        "manual": StaticProvider(_raw("GOLD_CNY", "manual", 1040.0, market_status="manual")),
    }

    selected = route_symbol(instrument, providers, RouterConfig(provider_mode="live"))

    assert providers["akshare"].called is False
    assert selected.source == "manual"


def test_all_attempts_fail_final_record_contains_attempts():
    instrument = _instrument("601899.SH", provider_priority=["akshare", "mock"])
    providers = {
        "akshare": StaticProvider(exc=ConnectionError("akshare down")),
        "mock": StaticProvider(),
    }

    selected = route_symbol(instrument, providers, RouterConfig(provider_mode="live", provider_policy="diagnostic"))

    assert "provider_error" in selected.quality_issues or "symbol_not_found" in selected.quality_issues
    assert selected.provider_diagnostics["selected_attempt_status"] == "failed"
    assert len(selected.provider_diagnostics["provider_attempts"]) >= 2
    assert selected.provider_diagnostics["provider_attempts"][0]["provider"] == "eastmoney_direct"


def test_provider_health_report_shows_attempts_by_symbol_and_fallback_used():
    instrument = _instrument("601899.SH", provider_priority=["akshare", "mock"])
    providers = {
        "akshare": StaticProvider(_raw("601899.SH", "akshare", None, quality_issues=["provider_error"])),
        "mock": StaticProvider(_raw("601899.SH", "mock", 18.42)),
    }
    raw = route_symbol(instrument, providers, RouterConfig(provider_mode="live"))
    record = _record(raw, required=True)

    report = build_provider_health_report([record], provider_mode="live")

    assert "Provider attempts by symbol" in report
    assert "### 601899.SH" in report
    assert "fallback_used: True" in report
    assert "provider=akshare" in report
    assert "provider=mock" in report


def test_data_completeness_report_shows_mock_fallback_not_usable():
    raw = route_symbol(
        _instrument("601899.SH", provider_priority=["akshare", "mock"]),
        {
            "akshare": StaticProvider(_raw("601899.SH", "akshare", None, quality_issues=["provider_error"])),
            "mock": StaticProvider(_raw("601899.SH", "mock", 18.42)),
        },
        RouterConfig(provider_mode="live"),
    )
    record = _record(raw, required=True)
    record.is_stale = True
    record.stale_reason = "mock_fallback_not_allowed: mock fallback 不可用于具体操作建议"

    report = build_completeness_report([record])

    assert "mock fallback 不可用于具体操作建议" in report
    assert get_blocking_records([record])[0]["blocking_reason"] == "mock_fallback_not_allowed"


def test_primary_failure_does_not_block_when_fallback_is_usable():
    raw = route_symbol(
        _instrument("601899.SH", provider_priority=["akshare", "mock"], allow_mock_fallback_for_operation=True),
        {
            "akshare": StaticProvider(_raw("601899.SH", "akshare", None, quality_issues=["provider_error"])),
            "mock": StaticProvider(_raw("601899.SH", "mock", 18.42)),
        },
        RouterConfig(provider_mode="live"),
    )
    record = _record(raw, required=True)

    assert get_blocking_records([record]) == []


def test_provider_mode_mock_skips_akshare():
    watchlist = Watchlist(
        projects={
            "energy": WatchProject(
                display_name="energy",
                allow_full_detail=True,
                instruments=[_instrument("601899.SH", provider_priority=["akshare", "mock"])],
            )
        }
    )
    providers = {
        "akshare": StaticProvider(exc=AssertionError("akshare should not be called")),
        "mock": StaticProvider(_raw("601899.SH", "mock", 18.42)),
    }

    prices = collect_routed_prices(watchlist, providers, RouterConfig(provider_mode="mock"))

    assert providers["akshare"].called is False
    assert prices["601899.SH"].source == "mock"


def test_tech_price_block_grouping_survives_routing_diagnostics():
    records = [
        _record(_raw("159819.SZ", "akshare", 0.921), project="tech", asset_role="ai_tech_equity"),
        _record(_raw("515880.SH", "akshare", 1.084), project="tech", asset_role="communication_tech_equity"),
        _record(_raw("510300.SH", "akshare", 3.921), project="tech", asset_role="non_tech_broad_base_etf"),
        _record(_raw("GOLD_CNY", "manual", 1040.0), project="tech", asset_role="defense_or_potential_tech_funding"),
    ]

    report = build_tech_block(records)

    assert "AI / 人工智能ETF" in report
    assert "通信 / 科技ETF" in report
    assert "非科技宽基单独列示" in report
    assert "黄金防守仓 / 潜在转科技资金" in report


def _instrument(
    symbol: str,
    provider: str = "akshare",
    provider_priority: list[str] | None = None,
    market: str = "CN",
    allow_mock_fallback_for_operation: bool = False,
    allow_manual_fallback_for_operation: bool = False,
) -> Instrument:
    return Instrument(
        symbol=symbol,
        name=symbol,
        market=market,
        provider=provider,
        provider_priority=provider_priority,
        required_for_operation=True,
        allow_mock_fallback_for_operation=allow_mock_fallback_for_operation,
        allow_manual_fallback_for_operation=allow_manual_fallback_for_operation,
    )


def _raw(
    symbol: str,
    source: str,
    price: float | None,
    quality_issues: list[str] | None = None,
    market_status: str = "closed",
) -> RawPrice:
    now = datetime(2026, 5, 18, 8, 0, tzinfo=timezone.utc)
    return RawPrice(
        symbol=symbol,
        price=price,
        currency="CNY",
        source=source,
        quote_time=now if price is not None else None,
        fetch_time=now,
        market_status=market_status,
        quality_issues=quality_issues or [],
    )


def _record(
    raw: RawPrice,
    project: str = "energy",
    required: bool = False,
    asset_role: str | None = None,
) -> PriceRecord:
    return PriceRecord(
        project=project,
        symbol=raw.symbol,
        name=raw.symbol,
        market=raw.market or "CN",
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
        asset_role=asset_role,
    )
