from __future__ import annotations

from datetime import datetime, timezone

from market_price_guard.models import Instrument, PriceRecord, RawPrice, Watchlist, WatchProject
from market_price_guard.normalize import normalize_records
from market_price_guard.provider_router import ProviderRuntimeBudget, RouterConfig, collect_routed_prices, route_symbol
from market_price_guard.report import build_completeness_report, build_provider_health_report, get_blocking_records, build_tech_block
from market_price_guard.yfinance_circuit import YFinanceCircuitBreaker


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


def test_energy_a_share_operation_routes_through_eastmoney_reference_path():
    raw = route_symbol(
        _instrument("600938.SH", provider_priority=["akshare", "yfinance", "mock"], project_scope="energy", asset_type="stock"),
        {
            "eastmoney_direct": StaticProvider(_raw("600938.SH", "eastmoney_direct", 7.42)),
            "akshare": StaticProvider(_raw("600938.SH", "akshare", 7.4)),
        },
        RouterConfig(provider_mode="live", provider_policy="fast"),
    )

    assert raw.provider_diagnostics["effective_provider_chain"][0] == "eastmoney_direct"
    assert raw.provider_diagnostics["selected_provider"] == "eastmoney_direct"
    assert raw.provider_diagnostics["actual_provider_attempted"] == ["eastmoney_direct"]
    assert raw.provider_diagnostics["provider_planned_chain"] != raw.provider_diagnostics["actual_provider_attempted"]
    assert raw.provider_diagnostics["usable_for_operation"] is False


def test_energy_route_does_not_fallback_to_tech_account_for_a_share():
    raw = route_symbol(
        _instrument("600938.SH", provider_priority=["akshare", "mock"], project_scope="energy", asset_type="stock"),
        {"eastmoney_direct": StaticProvider(_raw("600938.SH", "eastmoney_direct", 7.42))},
        RouterConfig(provider_mode="live", provider_policy="fast"),
    )

    assert raw.provider_diagnostics["selected_provider"] == "eastmoney_direct"
    assert raw.provider_diagnostics["normalized_symbol"] == "600938.SH"
    assert "tech" not in str(raw.provider_diagnostics).lower()


def test_scan_fast_stock_uses_eastmoney_and_skips_akshare_stock_fallback():
    providers = {
        "eastmoney_direct": StaticProvider(_raw("300308.SZ", "eastmoney_direct", 112.3)),
        "akshare": StaticProvider(_raw("300308.SZ", "akshare", 111.0)),
        "yfinance": StaticProvider(_raw("300308.SZ", "yfinance", 112.0)),
    }
    instrument = Instrument(
        symbol="300308.SZ",
        name="300308.SZ",
        market="CN",
        provider="eastmoney_direct",
        provider_priority=["eastmoney_direct", "yfinance", "akshare", "mock"],
        asset_type="stock",
        universe_type="scan_universe",
        required_for_operation=False,
    )

    raw = route_symbol(
        instrument,
        providers,
        RouterConfig(provider_mode="live", provider_policy="fast", quote_purpose="reference", scan_mode="fast"),
    )

    assert raw.provider_diagnostics["effective_provider_chain"] == ["eastmoney_direct", "mock"]
    assert raw.provider_diagnostics["selected_provider"] == "eastmoney_direct"
    assert providers["akshare"].called is False
    assert providers["yfinance"].called is False


def test_scan_diagnostic_stock_keeps_full_fallback_chain():
    instrument = Instrument(
        symbol="300308.SZ",
        name="300308.SZ",
        market="CN",
        provider="eastmoney_direct",
        provider_priority=["eastmoney_direct", "yfinance", "akshare", "mock"],
        asset_type="stock",
        universe_type="scan_universe",
        required_for_operation=False,
    )

    raw = route_symbol(
        instrument,
        {
            "eastmoney_direct": StaticProvider(_raw("300308.SZ", "eastmoney_direct", 112.3)),
            "akshare": StaticProvider(_raw("300308.SZ", "akshare", 111.0)),
            "yfinance": StaticProvider(_raw("300308.SZ", "yfinance", 112.0)),
        },
        RouterConfig(provider_mode="live", provider_policy="fast", quote_purpose="reference", scan_mode="diagnostic"),
    )

    assert raw.provider_diagnostics["effective_provider_chain"] == ["eastmoney_direct", "yfinance", "akshare", "mock"]


def test_yfinance_circuit_skips_following_symbols_after_rate_limit():
    circuit = YFinanceCircuitBreaker()
    first = route_symbol(
        _instrument("00883.HK", provider_priority=["yfinance", "mock"], market="HK"),
        {
            "yfinance": StaticProvider(exc=RuntimeError("YFRateLimitError: Too Many Requests")),
            "mock": StaticProvider(_raw("00883.HK", "mock", 21.0)),
        },
        RouterConfig(provider_mode="live", provider_policy="fast", yfinance_circuit=circuit),
    )
    second_yf = StaticProvider(_raw("601899.SH", "yfinance", 18.0))
    second = route_symbol(
        _instrument("601899.SH", provider_priority=["yfinance", "mock"]),
        {
            "yfinance": second_yf,
            "mock": StaticProvider(_raw("601899.SH", "mock", 18.0)),
        },
        RouterConfig(provider_mode="live", provider_policy="fast", yfinance_circuit=circuit),
    )

    assert circuit.open is True
    assert circuit.reason == "rate_limited"
    assert first.provider_diagnostics["selected_provider"] == "mock"
    assert second_yf.called is False
    assert second.provider_diagnostics["selected_provider"] == "mock"
    assert circuit.skipped_by_circuit_count == 1
    assert circuit.base_quote_skipped_by_circuit_count == 1
    assert any(
        attempt["provider"] == "yfinance" and attempt["reason"] == "fallback_skipped_yfinance_circuit_open"
        for attempt in second.provider_diagnostics["provider_attempts"]
    )


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
        attempt["reason"] == "selected_provider_success_policy_skip"
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


def test_mock_fallback_is_not_reference_or_operation_usable_after_normalization():
    raw = route_symbol(
        _instrument("601899.SH", provider_priority=["akshare", "mock"]),
        {
            "akshare": StaticProvider(_raw("601899.SH", "akshare", None, quality_issues=["provider_error"])),
            "mock": StaticProvider(_raw("601899.SH", "mock", 18.42)),
        },
        RouterConfig(provider_mode="live", provider_policy="diagnostic"),
    )
    record = _record(raw, required=True)

    assert raw.source == "mock_fallback"
    assert record.usable_for_reference is False
    assert get_blocking_records([record])[0]["blocking_reason"] == "mock_fallback_not_allowed"


def test_hk_provider_failure_reason_is_explicit_in_health_report():
    raw = route_symbol(
        _instrument("00883.HK", provider_priority=["yfinance", "akshare", "mock"], market="HK", project_scope="energy", asset_type="stock"),
        {
            "yfinance": StaticProvider(exc=TimeoutError("hk timeout")),
            "akshare": StaticProvider(_raw("00883.HK", "akshare", None, quality_issues=["provider_error"])),
            "mock": StaticProvider(_raw("00883.HK", "mock", 21.0)),
        },
        RouterConfig(provider_mode="live", provider_policy="fast", timeout_seconds=0.001),
    )
    record = _record(raw, required=True)

    report = build_provider_health_report([record], provider_mode="live")

    assert "provider_timeout" in report or "hk_provider_error" in report
    assert "00883.HK" in report
    assert raw.provider_diagnostics["provider_planned_chain"] == ["yfinance", "akshare", "mock"]
    assert raw.provider_diagnostics["actual_provider_attempted"] == ["yfinance", "mock"]
    assert raw.provider_diagnostics["provider_skip_reasons"]["akshare"] == "hk_akshare_skipped_after_fast_provider_failure_budget"


def test_fast_hk_route_skips_akshare_after_yfinance_failure_budget():
    akshare = StaticProvider(_raw("00883.HK", "akshare", 21.0))
    raw = route_symbol(
        _instrument("00883.HK", provider_priority=["yfinance", "akshare", "mock"], market="HK", project_scope="energy", asset_type="stock"),
        {
            "yfinance": StaticProvider(_raw("00883.HK", "yfinance", None, quality_issues=["provider_timeout", "provider_error"])),
            "akshare": akshare,
            "mock": StaticProvider(_raw("00883.HK", "mock", 21.0)),
        },
        RouterConfig(provider_mode="live", provider_policy="fast"),
    )

    assert akshare.called is False
    assert raw.provider_diagnostics["provider_skip_reasons"]["akshare"] == "hk_akshare_skipped_after_fast_provider_failure_budget"


def test_a_share_route_budget_failure_is_not_generic_symbol_not_found():
    raw = route_symbol(
        _instrument("600938.SH", provider_priority=["mock"], project_scope="energy", asset_type="stock"),
        {"mock": StaticProvider()},
        RouterConfig(
            provider_mode="live",
            provider_policy="fast",
            quote_purpose="reference",
            runtime_budget=ProviderRuntimeBudget(max_failed_attempts_per_provider=0),
        ),
    )

    assert "provider_error" in raw.quality_issues
    assert "provider_skipped_by_failure_budget" in raw.quality_issues
    assert "symbol_not_found" not in raw.quality_issues


def test_runtime_budget_circuit_skips_provider_without_counting_attempted():
    budget = ProviderRuntimeBudget(timeout_seconds=0.001, max_failed_attempts_per_provider=1, failure_threshold=1)
    first = route_symbol(
        _instrument("601899.SH", provider_priority=["akshare", "mock"], asset_type="stock"),
        {
            "eastmoney_direct": StaticProvider(_raw("601899.SH", "eastmoney_direct", None, quality_issues=["provider_error"])),
            "akshare": StaticProvider(_raw("601899.SH", "akshare", None, quality_issues=["provider_error"])),
            "mock": StaticProvider(_raw("601899.SH", "mock", 18.42)),
        },
        RouterConfig(provider_mode="live", provider_policy="diagnostic", runtime_budget=budget),
    )
    second_provider = StaticProvider(_raw("601985.SH", "eastmoney_direct", 7.25))
    second = route_symbol(
        _instrument("601985.SH", provider_priority=["akshare", "mock"], asset_type="stock"),
        {"eastmoney_direct": second_provider, "mock": StaticProvider(_raw("601985.SH", "mock", 7.25))},
        RouterConfig(provider_mode="live", provider_policy="diagnostic", runtime_budget=budget),
    )

    assert first.provider_diagnostics["actual_provider_attempted"][0] == "eastmoney_direct"
    assert second_provider.called is False
    assert second.provider_diagnostics["provider_skip_reasons"]["eastmoney_direct"] == "skipped_by_provider_circuit"
    assert "eastmoney_direct" not in second.provider_diagnostics["actual_provider_attempted"]


def test_eastmoney_permission_denied_opens_runtime_circuit():
    budget = ProviderRuntimeBudget(failure_threshold=10, timeout_threshold=10)
    first = route_symbol(
        _instrument("601899.SH", provider_priority=["akshare", "mock"], asset_type="stock"),
        {
            "eastmoney_direct": StaticProvider(_raw("601899.SH", "eastmoney_direct", None, quality_issues=["provider_error", "provider_network_permission_denied"])),
            "mock": StaticProvider(_raw("601899.SH", "mock", 18.42)),
        },
        RouterConfig(provider_mode="live", provider_policy="diagnostic", runtime_budget=budget),
    )
    second_provider = StaticProvider(_raw("601985.SH", "eastmoney_direct", 7.25))
    second = route_symbol(
        _instrument("601985.SH", provider_priority=["akshare", "mock"], asset_type="stock"),
        {"eastmoney_direct": second_provider, "mock": StaticProvider(_raw("601985.SH", "mock", 7.25))},
        RouterConfig(provider_mode="live", provider_policy="diagnostic", runtime_budget=budget),
    )

    assert any(
        attempt["provider"] == "eastmoney_direct" and attempt["reason"] == "provider_network_permission_denied"
        for attempt in first.provider_diagnostics["provider_attempts"]
    )
    assert second_provider.called is False
    assert second.provider_diagnostics["provider_skip_reasons"]["eastmoney_direct"] == "skipped_by_provider_circuit"


def test_provider_health_summary_has_planned_actual_skip_counts():
    raw = route_symbol(
        _instrument("601899.SH", provider_priority=["akshare", "mock"], asset_type="stock"),
        {
            "eastmoney_direct": StaticProvider(_raw("601899.SH", "eastmoney_direct", 18.42)),
            "akshare": StaticProvider(_raw("601899.SH", "akshare", 18.4)),
            "mock": StaticProvider(_raw("601899.SH", "mock", 18.0)),
        },
        RouterConfig(provider_mode="live", provider_policy="diagnostic", quote_purpose="reference"),
    )
    report = build_provider_health_report([_record(raw)], provider_mode="live")

    assert "## Provider Health Summary" in report
    assert "planned_count" in report
    assert "actual_attempt_count" in report
    assert "skipped_count" in report
    assert "route_reason: account_generic_a_share_stock_route" in report


def test_run_level_quote_cache_records_success_and_hit_has_no_provider_attempt(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKET_GUARD_USE_QUOTE_RUN_CACHE", "1")
    monkeypatch.setenv("MARKET_GUARD_QUOTE_RUN_CACHE_DIR", str(tmp_path / "quote_cache"))
    instrument = _instrument("601899.SH", provider_priority=["akshare", "mock"], asset_type="stock")
    first_provider = StaticProvider(_raw("601899.SH", "akshare", 18.42))

    first = route_symbol(
        instrument,
        {"akshare": first_provider},
        RouterConfig(provider_mode="live", provider_policy="conservative", account="energy", layer="energy_scan", quote_purpose="reference"),
    )
    second_provider = StaticProvider(exc=AssertionError("cache hit should prevent provider call"))
    second = route_symbol(
        instrument,
        {"akshare": second_provider},
        RouterConfig(provider_mode="live", provider_policy="conservative", account="energy", layer="energy_watchlist", quote_purpose="reference"),
    )

    assert first.provider_diagnostics["cache_miss"] is True
    assert second_provider.called is False
    assert second.provider_diagnostics["cache_hit"] is True
    assert second.provider_diagnostics["actual_provider_attempted"] == []
    assert second.provider_diagnostics["provider_attempts"] == []
    assert second.provider_diagnostics["repeated_provider_call_prevented"] is True


def test_run_level_quote_cache_records_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKET_GUARD_USE_QUOTE_RUN_CACHE", "1")
    monkeypatch.setenv("MARKET_GUARD_QUOTE_RUN_CACHE_DIR", str(tmp_path / "quote_cache"))
    instrument = _instrument("601899.SH", provider_priority=["akshare"], asset_type="stock")

    first = route_symbol(
        instrument,
        {"akshare": StaticProvider(_raw("601899.SH", "akshare", None, quality_issues=["provider_error"]))},
        RouterConfig(provider_mode="live", provider_policy="conservative", account="energy", layer="energy_scan", quote_purpose="reference"),
    )
    second_provider = StaticProvider(exc=AssertionError("cached failure should prevent provider call"))
    second = route_symbol(
        instrument,
        {"akshare": second_provider},
        RouterConfig(provider_mode="live", provider_policy="conservative", account="energy", layer="energy_watchlist", quote_purpose="reference"),
    )

    assert first.price is None
    assert second_provider.called is False
    assert second.price is None
    assert second.provider_diagnostics["cache_hit"] is True
    assert second.provider_diagnostics["actual_provider_attempted"] == []


def test_reference_cache_does_not_upgrade_operation_quote(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKET_GUARD_USE_QUOTE_RUN_CACHE", "1")
    monkeypatch.setenv("MARKET_GUARD_QUOTE_RUN_CACHE_DIR", str(tmp_path / "quote_cache"))
    instrument = _instrument("159819.SZ", provider_priority=["akshare", "mock"], asset_type="etf")
    route_symbol(
        instrument,
        {"akshare": StaticProvider(_raw("159819.SZ", "akshare", 0.921))},
        RouterConfig(provider_mode="live", provider_policy="fast", account="tech", layer="tech_scan_ai", quote_purpose="reference"),
    )
    operation_provider = StaticProvider(_raw("159819.SZ", "akshare", 0.922))

    operation = route_symbol(
        instrument,
        {"akshare": operation_provider},
        RouterConfig(provider_mode="live", provider_policy="fast", account="tech", layer="tech_core", quote_purpose="operation"),
    )

    assert operation_provider.called is True
    assert operation.price == 0.922
    assert operation.provider_diagnostics["cache_miss"] is True
    assert operation.provider_diagnostics["cache_event"]["cache_status"] == "profile_insufficient"


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
    project_scope: str | None = None,
    asset_type: str | None = None,
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
        project_scope=project_scope,
        asset_type=asset_type,
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
