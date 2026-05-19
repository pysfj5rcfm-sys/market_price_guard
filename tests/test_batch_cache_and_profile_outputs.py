from __future__ import annotations

import pandas as pd

from market_price_guard.main import run_pipeline
from market_price_guard.models import Instrument
from market_price_guard.provider_router import RouterConfig, route_symbol
from market_price_guard.providers.akshare_provider import AkshareProvider
from market_price_guard.report import build_provider_health_report


def test_akshare_etf_full_interface_called_once_for_multiple_etfs(ak_factory, sample_etf_df):
    calls = {"fund_etf_spot_em": 0}

    def fund_etf_spot_em():
        calls["fund_etf_spot_em"] += 1
        return sample_etf_df()

    ak = ak_factory(fund_etf_spot_em=fund_etf_spot_em)
    provider = AkshareProvider(ak)

    prices = provider.fetch(["159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"])

    assert calls["fund_etf_spot_em"] == 1
    assert {symbol for symbol, raw in prices.items() if raw.price is not None} == {
        "159632.SZ",
        "513300.SH",
        "159819.SZ",
        "515880.SH",
        "510300.SH",
    }
    assert {symbol: raw.price for symbol, raw in prices.items()} == {
        "159632.SZ": 1.432,
        "513300.SH": 1.671,
        "159819.SZ": 0.921,
        "515880.SH": 1.084,
        "510300.SH": 3.921,
    }


def test_cached_etf_dataframe_is_rematched_for_each_symbol_through_router(ak_factory, sample_etf_df, failing_provider):
    calls = {"fund_etf_spot_em": 0}

    def fund_etf_spot_em():
        calls["fund_etf_spot_em"] += 1
        return sample_etf_df()

    akshare = AkshareProvider(ak_factory(fund_etf_spot_em=fund_etf_spot_em))
    providers = {"akshare": akshare, "mock": failing_provider}
    selected = {}
    for symbol in ["159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"]:
        selected[symbol] = route_symbol(_instrument(symbol, required=symbol != "510300.SH"), providers, RouterConfig(provider_mode="live"))

    assert calls["fund_etf_spot_em"] == 1
    assert {symbol: raw.price for symbol, raw in selected.items()} == {
        "159632.SZ": 1.432,
        "513300.SH": 1.671,
        "159819.SZ": 0.921,
        "515880.SH": 1.084,
        "510300.SH": 3.921,
    }
    assert all(raw.source == "akshare" for raw in selected.values())
    assert all(raw.provider_diagnostics["selected_provider"] == "akshare" for raw in selected.values())
    assert all(raw.provider_diagnostics["fallback_used"] is False for raw in selected.values())
    assert selected["159632.SZ"].provider_diagnostics["provider_attempts"][0]["from_cache"] is False
    for symbol in ["513300.SH", "159819.SZ", "515880.SH", "510300.SH"]:
        assert selected[symbol].provider_diagnostics["provider_attempts"][0]["from_cache"] is True
        assert selected[symbol].provider_diagnostics["provider_attempts"][0]["provider_status"] == "success"
    assert not providers["mock"].called


def test_akshare_cache_reuses_etf_failure(ak_factory):
    calls = {"fund_etf_spot_em": 0}

    def fund_etf_spot_em():
        calls["fund_etf_spot_em"] += 1
        raise RuntimeError("etf down")

    ak = ak_factory(fund_etf_spot_em=fund_etf_spot_em)
    provider = AkshareProvider(ak)

    first = provider.fetch(["159819.SZ"])["159819.SZ"]
    second = provider.fetch(["515880.SH"])["515880.SH"]

    assert calls["fund_etf_spot_em"] == 1
    assert "provider_error" in first.quality_issues
    assert "provider_error" in second.quality_issues
    assert second.provider_diagnostics["attempts"][0]["from_cache"] is True


def test_provider_health_report_shows_akshare_call_summary(ak_factory, sample_etf_df):
    ak = ak_factory(fund_etf_spot_em=sample_etf_df)
    provider = AkshareProvider(ak)
    prices = provider.fetch(["159819.SZ"])
    prices.update(provider.fetch(["515880.SH"]))
    records = [_record(raw) for raw in prices.values()]

    report = build_provider_health_report(records, provider_mode="live")

    assert "Provider call summary" in report
    assert "function_name=fund_etf_spot_em" in report
    assert "call_count=1" in report
    assert "cache_hits=1" in report
    assert "from_cache=True" in report


def test_akshare_sh_and_sz_fallback_interfaces_called_once_each(ak_factory):
    calls = {"stock_zh_a_spot_em": 0, "stock_sh_a_spot_em": 0, "stock_sz_a_spot_em": 0}

    def primary():
        calls["stock_zh_a_spot_em"] += 1
        raise ConnectionError("primary down")

    def sh():
        calls["stock_sh_a_spot_em"] += 1
        return pd.DataFrame(
            [
                {"code": "601899", "name": "Zijin", "price": 18.42, "update_time": "2026-05-18 14:57:00+08:00"},
                {"code": "601985", "name": "CNNP", "price": 10.91, "update_time": "2026-05-18 14:57:00+08:00"},
            ]
        )

    def sz():
        calls["stock_sz_a_spot_em"] += 1
        return pd.DataFrame([{"code": "003816", "name": "CGN", "price": 4.27, "update_time": "2026-05-18 14:59:00+08:00"}])

    provider = AkshareProvider(ak_factory(stock_zh_a_spot_em=primary, stock_sh_a_spot_em=sh, stock_sz_a_spot_em=sz))
    prices = provider.fetch(["601899.SH"])
    prices.update(provider.fetch(["601985.SH"]))
    prices.update(provider.fetch(["003816.SZ"]))

    assert calls == {"stock_zh_a_spot_em": 1, "stock_sh_a_spot_em": 1, "stock_sz_a_spot_em": 1}
    assert prices["601899.SH"].price == 18.42
    assert prices["601985.SH"].price == 10.91
    assert prices["003816.SZ"].price == 4.27


def test_profile_tech_outputs_are_scoped(tmp_path):
    output_dir = tmp_path / "tech"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)
    index = (output_dir / "index.md").read_text(encoding="utf-8")
    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")

    assert (output_dir / "tech_price_block.md").exists()
    assert not (output_dir / "energy_price_block.md").exists()
    assert not (output_dir / "controller_price_summary.md").exists()
    assert "tech_price_block.md" in index
    assert "energy_price_block.md" not in index
    assert "controller_price_summary.md" not in index
    assert set(df["project"]) == {"tech"}


def test_profile_energy_outputs_are_scoped(tmp_path):
    output_dir = tmp_path / "energy"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="energy", strict=True)
    index = (output_dir / "index.md").read_text(encoding="utf-8")
    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")

    assert (output_dir / "energy_price_block.md").exists()
    assert not (output_dir / "tech_price_block.md").exists()
    assert not (output_dir / "controller_price_summary.md").exists()
    assert "energy_price_block.md" in index
    assert "tech_price_block.md" not in index
    assert "controller_price_summary.md" not in index
    assert set(df["project"]) == {"energy"}


def test_profile_all_outputs_only_controller_summary(tmp_path):
    output_dir = tmp_path / "all"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="all", strict=True)
    index = (output_dir / "index.md").read_text(encoding="utf-8")

    assert (output_dir / "controller_price_summary.md").exists()
    assert not (output_dir / "energy_price_block.md").exists()
    assert not (output_dir / "tech_price_block.md").exists()
    assert "controller_price_summary.md" in index
    assert "energy_price_block.md" not in index
    assert "tech_price_block.md" not in index


def test_diagnostic_policy_outputs_no_project_blocks(tmp_path):
    output_dir = tmp_path / "diagnostic"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="all", provider_policy="diagnostic")
    index = (output_dir / "index.md").read_text(encoding="utf-8")

    assert not (output_dir / "controller_price_summary.md").exists()
    assert not (output_dir / "energy_price_block.md").exists()
    assert not (output_dir / "tech_price_block.md").exists()
    assert "controller_price_summary.md" not in index
    assert "energy_price_block.md" not in index
    assert "tech_price_block.md" not in index


def _instrument(symbol: str, required: bool = True) -> Instrument:
    return Instrument(
        symbol=symbol,
        name=symbol,
        market="CN",
        provider="akshare",
        provider_priority=["akshare", "mock"],
        required_for_operation=required,
    )


def _record(raw):
    from market_price_guard.models import PriceRecord

    return PriceRecord(
        project="tech",
        symbol=raw.symbol,
        name=raw.name or raw.symbol,
        market=raw.market or "CN",
        price=raw.price,
        currency=raw.currency,
        source=raw.source,
        quote_time=raw.quote_time,
        fetch_time=raw.fetch_time,
        market_status=raw.market_status,
        is_stale=bool(raw.quality_issues),
        stale_reason=", ".join(raw.quality_issues),
        required_for_operation=True,
        quality_issues=raw.quality_issues,
        provider_diagnostics=raw.provider_diagnostics,
    )
