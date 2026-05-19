from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        path = item.path.name
        if "live" in item.keywords:
            continue
        if path in {"test_akshare_provider.py", "test_yfinance_provider.py", "test_provider_router.py", "test_batch_cache_and_profile_outputs.py"}:
            item.add_marker(pytest.mark.provider)
        elif path in {"test_output_contract.py", "test_quote_trust_tier.py"}:
            item.add_marker(pytest.mark.contract)
        elif path == "test_index_and_scripts.py":
            item.add_marker(pytest.mark.script)
        else:
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def stale_rules_factory(tmp_path):
    def _write(default_max_age: int, manual_max_age: int) -> Path:
        stale_rules = tmp_path / "stale_rules.yaml"
        stale_rules.write_text(
            f"""
default:
  max_age_seconds_open: {default_max_age}
  max_age_seconds_closed: {default_max_age}
manual:
  max_age_seconds: {manual_max_age}
MANUAL:
  max_age_seconds: {manual_max_age}
markets: {{}}
""".strip(),
            encoding="utf-8",
        )
        return stale_rules

    return _write


@pytest.fixture
def sample_etf_df():
    def _build() -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"code": "159632", "name": "Nasdaq ETF", "price": 1.432, "update_time": "2026-05-18 15:34:03+08:00"},
                {"code": "513300", "name": "Nasdaq ETF", "price": 1.671, "update_time": "2026-05-18 15:34:03+08:00"},
                {"code": "159819", "name": "AI ETF", "price": 0.921, "update_time": "2026-05-18 15:34:21+08:00"},
                {"code": "515880", "name": "Communication ETF", "price": 1.084, "update_time": "2026-05-18 15:34:21+08:00"},
                {"code": "510300", "name": "CSI300 ETF", "price": 3.921, "update_time": "2026-05-18 15:34:21+08:00"},
            ]
        )

    return _build


@pytest.fixture
def ak_factory():
    def _factory(**overrides):
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

    return _factory


class FailingProvider:
    def __init__(self):
        self.called = False

    def fetch(self, symbols):
        self.called = True
        raise AssertionError(f"fallback should not be called for {symbols}")


@pytest.fixture
def failing_provider():
    return FailingProvider()
