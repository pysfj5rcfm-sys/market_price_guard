from __future__ import annotations

import pandas as pd

from market_price_guard.providers.akshare_provider import AkshareProvider
from market_price_guard.uat_run_cache import ENV_CACHE_DIR, ENV_USE_CACHE, load_manifest


def _etf_df(price: float = 1.23) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "代码": "159819",
                "名称": "人工智能ETF",
                "最新价": price,
                "昨收": price - 0.01,
                "今开": price - 0.005,
                "最高": price + 0.01,
                "最低": price - 0.02,
                "成交量": 1000,
                "成交额": 1230,
                "更新时间": "2026-05-21 10:00:00",
            }
        ]
    )


class _AkModule:
    def __init__(self, func):
        self.fund_etf_spot_em = func


def test_uat_run_cache_first_call_miss_then_second_provider_instance_hit(monkeypatch, tmp_path):
    cache_dir = tmp_path / "uat_cache"
    monkeypatch.setenv(ENV_USE_CACHE, "1")
    monkeypatch.setenv(ENV_CACHE_DIR, str(cache_dir))
    calls = {"fund_etf_spot_em": 0}

    def live_fetch():
        calls["fund_etf_spot_em"] += 1
        return _etf_df()

    first = AkshareProvider(_AkModule(live_fetch)).fetch(["159819.SZ"])["159819.SZ"]
    second = AkshareProvider(_AkModule(lambda: (_ for _ in ()).throw(AssertionError("cache should be used")))).fetch(["159819.SZ"])["159819.SZ"]

    assert calls["fund_etf_spot_em"] == 1
    assert first.source == "akshare"
    assert second.source == "akshare"
    assert second.provider_diagnostics["attempts"][0]["cache_status"] == "hit"
    assert second.provider_diagnostics["attempts"][0]["cache_scope"] == "uat_run"
    manifest = load_manifest(cache_dir)
    assert manifest["miss_count"] == 1
    assert manifest["hit_count"] == 1
    assert manifest["row_count"] == 1


def test_uat_run_cache_disabled_keeps_live_provider_behavior(monkeypatch, tmp_path):
    monkeypatch.delenv(ENV_USE_CACHE, raising=False)
    monkeypatch.setenv(ENV_CACHE_DIR, str(tmp_path / "uat_cache"))
    calls = {"fund_etf_spot_em": 0}

    def live_fetch():
        calls["fund_etf_spot_em"] += 1
        return _etf_df()

    AkshareProvider(_AkModule(live_fetch)).fetch(["159819.SZ"])
    AkshareProvider(_AkModule(live_fetch)).fetch(["159819.SZ"])

    assert calls["fund_etf_spot_em"] == 2
    assert not (tmp_path / "uat_cache" / "akshare_fund_etf_spot_em.csv").exists()


def test_uat_run_cache_corrupt_file_falls_back_to_live_fetch(monkeypatch, tmp_path):
    cache_dir = tmp_path / "uat_cache"
    cache_dir.mkdir()
    (cache_dir / "akshare_fund_etf_spot_em.csv").write_bytes(b"\xff\xff")
    monkeypatch.setenv(ENV_USE_CACHE, "1")
    monkeypatch.setenv(ENV_CACHE_DIR, str(cache_dir))
    calls = {"fund_etf_spot_em": 0}

    def live_fetch():
        calls["fund_etf_spot_em"] += 1
        return _etf_df(1.25)

    record = AkshareProvider(_AkModule(live_fetch)).fetch(["159819.SZ"])["159819.SZ"]

    assert calls["fund_etf_spot_em"] == 1
    assert record.price == 1.25
    manifest = load_manifest(cache_dir)
    assert manifest["cache_error_count"] == 1
    assert manifest["bypass_count"] == 1
