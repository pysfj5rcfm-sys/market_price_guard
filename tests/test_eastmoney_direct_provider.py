from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from market_price_guard.main import EXIT_OK, run_pipeline
from market_price_guard.models import Instrument, WatchProject, Watchlist
from market_price_guard.normalize import load_watchlist, load_yaml, normalize_records
from market_price_guard.provider_router import RouterConfig, route_symbol
from market_price_guard.providers.akshare_provider import AkshareProvider
from market_price_guard.providers.eastmoney_direct_provider import (
    EastmoneyDirectProvider,
    eastmoney_secid_for_symbol,
)
from market_price_guard.providers.mock_provider import MockProvider
from market_price_guard.providers.yfinance_provider import YFinanceProvider
from market_price_guard.report import build_completeness_report, build_debug_bundle, build_provider_health_report, build_upload_bundle, get_blocking_records


ETF_SYMBOLS = ["159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"]
TECH_CORE_SYMBOLS = [*ETF_SYMBOLS, "159516.SZ"]


def test_eastmoney_secid_mapping():
    assert eastmoney_secid_for_symbol("159632.SZ") == "0.159632"
    assert eastmoney_secid_for_symbol("159819.SZ") == "0.159819"
    assert eastmoney_secid_for_symbol("003816.SZ") == "0.003816"
    assert eastmoney_secid_for_symbol("513300.SH") == "1.513300"
    assert eastmoney_secid_for_symbol("515880.SH") == "1.515880"
    assert eastmoney_secid_for_symbol("510300.SH") == "1.510300"
    assert eastmoney_secid_for_symbol("601899.SH") == "1.601899"
    assert eastmoney_secid_for_symbol("601985.SH") == "1.601985"


def test_eastmoney_provider_parses_valid_response():
    provider = EastmoneyDirectProvider(http_get=lambda url, params, timeout: _response(price=1.234, code="159819", name="人工智能ETF"))
    raw = provider.fetch(["159819.SZ"])["159819.SZ"]

    assert raw.source == "eastmoney_direct"
    assert raw.price == 1.234
    assert raw.currency == "CNY"
    assert raw.quote_time is not None
    assert raw.quote_time.tzinfo is not None
    assert raw.provider_diagnostics["secid"] == "0.159819"
    assert "assumed_currency_cny" in raw.quality_issues


def test_eastmoney_request_includes_secid_and_uses_headers():
    captured = {}

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return _response(price=1.234)

    provider = EastmoneyDirectProvider(http_get=fake_get)
    provider.fetch(["159819.SZ"])

    assert captured["params"]["secid"] == "0.159819"
    assert captured["url"].startswith("https://push2.eastmoney.com")

    from market_price_guard.providers.eastmoney_direct_provider import _eastmoney_headers

    headers = _eastmoney_headers()
    assert headers["User-Agent"]
    assert headers["Referer"] == "https://quote.eastmoney.com/"


def test_eastmoney_provider_error_cases():
    cases = [
        (_response(price=None), "invalid_price"),
        (_response(price=0), "invalid_price"),
        (_response(quote_time=None), "quote_time_missing"),
        ({"rc": 0, "data": {}}, "provider_error"),
        ({"rc": 102, "data": {"f43": 1.0}}, "provider_error"),
    ]
    for payload, expected_issue in cases:
        provider = EastmoneyDirectProvider(http_get=lambda url, params, timeout, payload=payload: payload)
        raw = provider.fetch(["159819.SZ"])["159819.SZ"]

        assert expected_issue in raw.quality_issues


def test_eastmoney_trust_tier_and_operation_blocking():
    provider = EastmoneyDirectProvider(http_get=lambda url, params, timeout: _response(price=1.234))
    raw = provider.fetch(["159819.SZ"])["159819.SZ"]
    records = normalize_records(
        _watchlist("159819.SZ"),
        {"159819.SZ": raw},
        load_yaml(__import__("pathlib").Path("config/stale_rules.yaml")),
        now=datetime(2026, 5, 19, 7, 0, tzinfo=timezone.utc),
    )
    record = records[0]

    assert record.quote_trust_tier == "reference"
    assert record.usable_for_reference is True
    assert record.usable_for_operation is False
    assert record.confirmation_required is True
    assert "Eastmoney Direct" in record.reference_note
    assert get_blocking_records(records)[0]["blocking_reason"] == "reference_tier_requires_operation_confirmation"


def test_reference_tech_chain_uses_eastmoney_before_yfinance_and_akshare(monkeypatch, tmp_path):
    calls = {"eastmoney": 0, "yfinance": 0, "akshare": 0}

    def eastmoney_fetch(self, symbols):
        calls["eastmoney"] += 1
        return {symbol: _raw(symbol, "eastmoney_direct", 1.0 + index / 100) for index, symbol in enumerate(symbols)}

    def yfinance_fetch(self, symbols):
        calls["yfinance"] += 1
        return {
            symbol: _raw(symbol, "yfinance", 1.0 + index / 100)
            for index, symbol in enumerate(symbols)
            if symbol in ETF_SYMBOLS
        }

    def akshare_fetch(self, symbols):
        calls["akshare"] += 1
        return {symbol: _raw(symbol, "akshare", 2.0 + index / 100) for index, symbol in enumerate(symbols) if symbol in TECH_CORE_SYMBOLS}

    monkeypatch.setattr(EastmoneyDirectProvider, "fetch", eastmoney_fetch)
    monkeypatch.setattr(YFinanceProvider, "fetch", yfinance_fetch)
    monkeypatch.setattr(AkshareProvider, "fetch", akshare_fetch)

    output_dir = tmp_path / "tech_reference"
    result = run_pipeline(
        output_dir=output_dir,
        provider_mode="live",
        provider_policy="fast",
        profile="tech",
        quote_purpose="reference",
    )
    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")
    health = (output_dir / "provider_health_report.md").read_text(encoding="utf-8")
    upload = (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    debug = (output_dir / "debug_bundle.md").read_text(encoding="utf-8")
    completeness = (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_OK
    assert calls["yfinance"] == len(ETF_SYMBOLS)
    assert calls["akshare"] == 1
    assert set(df[df["symbol"].isin(ETF_SYMBOLS)]["selected_provider"]) == {"eastmoney_direct"}
    assert set(df[df["symbol"].isin(ETF_SYMBOLS)]["quote_trust_tier"]) == {"reference"}
    assert set(df[df["symbol"].isin(ETF_SYMBOLS)]["usable_for_operation"].astype(str)) == {"False"}
    assert "effective_provider_chain: eastmoney_direct, yfinance, akshare, mock" in health
    assert "selected_provider=eastmoney_direct" in upload or "eastmoney_direct" in upload
    assert "eastmoney_direct" in debug
    assert "not official exchange real-time feed" in completeness
    assert (output_dir / "price_reconciliation_report.md").exists()
    assert not (output_dir / "energy_price_block.md").exists()
    assert not (output_dir / "controller_price_summary.md").exists()


def test_operation_tech_path_stays_akshare_first(monkeypatch, tmp_path):
    calls = {"eastmoney": 0, "akshare": 0}

    def eastmoney_fetch(self, symbols):
        calls["eastmoney"] += 1
        raise AssertionError("operation tech path should not call Eastmoney Direct")

    def akshare_fetch(self, symbols):
        calls["akshare"] += 1
        return {symbol: _raw(symbol, "akshare", 2.0 + index / 100) for index, symbol in enumerate(symbols) if symbol in ETF_SYMBOLS}

    monkeypatch.setattr(EastmoneyDirectProvider, "fetch", eastmoney_fetch)
    monkeypatch.setattr(AkshareProvider, "fetch", akshare_fetch)

    output_dir = tmp_path / "tech_operation"
    run_pipeline(
        output_dir=output_dir,
        provider_mode="live",
        provider_policy="fast",
        profile="tech",
        quote_purpose="operation",
        strict=True,
    )
    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")

    assert calls["eastmoney"] == 0
    assert set(df[df["symbol"].isin(ETF_SYMBOLS)]["selected_provider"]) == {"akshare"}


def test_diagnostic_chain_includes_eastmoney_direct_attempt():
    raw = route_symbol(
        _instrument("159819.SZ", provider_priority=["akshare", "mock"]),
        {"eastmoney_direct": _StaticProvider(_raw("159819.SZ", "eastmoney_direct", 1.0))},
        RouterConfig(provider_mode="live", provider_policy="diagnostic"),
    )

    assert raw.provider_diagnostics["effective_provider_chain"][0] == "eastmoney_direct"
    assert raw.provider_diagnostics["selected_provider"] == "eastmoney_direct"


def test_reports_include_eastmoney_direct_limitation():
    record = normalize_records(
        _watchlist("159819.SZ"),
        {"159819.SZ": _raw("159819.SZ", "eastmoney_direct", 1.0)},
        load_yaml(__import__("pathlib").Path("config/stale_rules.yaml")),
        now=datetime(2026, 5, 19, 7, 0, tzinfo=timezone.utc),
    )[0]

    assert "Eastmoney Direct" in build_completeness_report([record])
    assert "eastmoney_direct" in build_provider_health_report([record], provider_mode="live")
    assert "eastmoney_direct" in build_upload_bundle([record], __import__("pathlib").Path("outputs"), provider_mode="live", runtime={"quote_purpose": "reference", "profile": "tech"})
    assert "eastmoney_direct" in build_debug_bundle([record], __import__("pathlib").Path("outputs"), provider_mode="live", runtime={"quote_purpose": "reference", "profile": "tech"})


def test_provider_health_and_debug_bundle_show_eastmoney_secid():
    provider = EastmoneyDirectProvider(http_get=lambda url, params, timeout: _response(price=1.234))
    raw = provider.fetch(["159819.SZ"])["159819.SZ"]
    records = normalize_records(
        _watchlist("159819.SZ"),
        {"159819.SZ": raw},
        load_yaml(__import__("pathlib").Path("config/stale_rules.yaml")),
        now=datetime(2026, 5, 19, 7, 0, tzinfo=timezone.utc),
    )
    health = build_provider_health_report(records, provider_mode="live")
    debug = build_debug_bundle(records, __import__("pathlib").Path("outputs"), provider_mode="live", runtime={"quote_purpose": "reference", "profile": "tech"})

    assert "secid=0.159819" in health
    assert "secid=0.159819" in debug
    assert "retry_count=" in debug


def _response(price=1.23, quote_time=1779163200, code="159819", name="人工智能ETF"):
    data = {"f43": price, "f57": code, "f58": name, "f86": quote_time}
    return {"rc": 0, "data": data}


def _watchlist(symbol: str) -> Watchlist:
    return Watchlist(
        projects={
            "tech": WatchProject(
                display_name="tech",
                allow_full_detail=True,
                instruments=[_instrument(symbol)],
            )
        }
    )


def _instrument(symbol: str, provider_priority: list[str] | None = None) -> Instrument:
    return Instrument(
        symbol=symbol,
        name=symbol,
        market="CN",
        provider="akshare",
        provider_priority=provider_priority or ["akshare", "mock"],
        required_for_operation=True,
        asset_role="ai_tech_equity",
    )


def _raw(symbol: str, source: str, price: float) -> object:
    quote_time = datetime(2026, 5, 19, 6, 55, tzinfo=timezone.utc)
    return __import__("market_price_guard.models", fromlist=["RawPrice"]).RawPrice(
        symbol=symbol,
        name=symbol,
        market="CN",
        price=price,
        currency="CNY",
        source=source,
        quote_time=quote_time,
        fetch_time=quote_time,
        market_status="open",
        provider_diagnostics={"provider": source, "function_name": f"{source}.mock", "selected_provider": source},
        quote_trust_tier="reference" if source == "eastmoney_direct" else None,
        confirmation_required=True if source == "eastmoney_direct" else None,
        operation_blocking_reason="reference_tier_requires_operation_confirmation" if source == "eastmoney_direct" else "",
        reference_note="Eastmoney Direct uses Eastmoney public web quote endpoint; not an official exchange real-time feed"
        if source == "eastmoney_direct"
        else "",
    )


class _StaticProvider:
    def __init__(self, raw):
        self.raw = raw

    def fetch(self, symbols):
        return {self.raw.symbol: self.raw}
