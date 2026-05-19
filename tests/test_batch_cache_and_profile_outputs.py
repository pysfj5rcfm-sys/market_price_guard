from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from market_price_guard.main import run_pipeline
from market_price_guard.providers.akshare_provider import AkshareProvider
from market_price_guard.report import build_provider_health_report


def test_akshare_etf_full_interface_called_once_for_multiple_etfs():
    calls = {"fund_etf_spot_em": 0}

    def fund_etf_spot_em():
        calls["fund_etf_spot_em"] += 1
        return _etf_df()

    ak = _ak(fund_etf_spot_em=fund_etf_spot_em)
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


def test_akshare_cache_reuses_etf_failure():
    calls = {"fund_etf_spot_em": 0}

    def fund_etf_spot_em():
        calls["fund_etf_spot_em"] += 1
        raise RuntimeError("etf down")

    ak = _ak(fund_etf_spot_em=fund_etf_spot_em)
    provider = AkshareProvider(ak)

    first = provider.fetch(["159819.SZ"])["159819.SZ"]
    second = provider.fetch(["515880.SH"])["515880.SH"]

    assert calls["fund_etf_spot_em"] == 1
    assert "provider_error" in first.quality_issues
    assert "provider_error" in second.quality_issues
    assert second.provider_diagnostics["attempts"][0]["from_cache"] is True


def test_provider_health_report_shows_akshare_call_summary():
    ak = _ak(fund_etf_spot_em=lambda: _etf_df())
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


def test_akshare_sh_and_sz_fallback_interfaces_called_once_each():
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

    provider = AkshareProvider(_ak(stock_zh_a_spot_em=primary, stock_sh_a_spot_em=sh, stock_sz_a_spot_em=sz))
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


def _ak(**overrides):
    defaults = {
        "stock_zh_a_spot_em": lambda: pd.DataFrame(),
        "stock_sh_a_spot_em": lambda: pd.DataFrame(),
        "stock_sz_a_spot_em": lambda: pd.DataFrame(),
        "stock_hk_spot_em": lambda: pd.DataFrame(),
        "stock_hk_main_board_spot_em": lambda: pd.DataFrame(),
        "stock_hsgt_sh_hk_spot_em": lambda: pd.DataFrame(),
        "fund_etf_spot_em": lambda: pd.DataFrame(),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _etf_df():
    return pd.DataFrame(
        [
            {"code": "159632", "name": "Nasdaq ETF", "price": 1.432, "update_time": "2026-05-18 15:34:03+08:00"},
            {"code": "513300", "name": "Nasdaq ETF", "price": 1.671, "update_time": "2026-05-18 15:34:03+08:00"},
            {"code": "159819", "name": "AI ETF", "price": 0.921, "update_time": "2026-05-18 15:34:21+08:00"},
            {"code": "515880", "name": "Communication ETF", "price": 1.084, "update_time": "2026-05-18 15:34:21+08:00"},
            {"code": "510300", "name": "CSI300 ETF", "price": 3.921, "update_time": "2026-05-18 15:34:21+08:00"},
        ]
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
