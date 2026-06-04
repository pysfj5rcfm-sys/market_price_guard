from __future__ import annotations

import pytest

from market_price_guard.admin_symbol_infer import canonicalize_symbol


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("159632", "159632.SZ"),
        ("513300", "513300.SH"),
        ("601899", "601899.SH"),
        ("003816", "003816.SZ"),
        ("300308", "300308.SZ"),
        ("688256", "688256.SH"),
        ("00883", "00883.HK"),
        ("QQQ", "QQQ"),
        ("GOLD_CNY", "GOLD_CNY"),
    ],
)
def test_admin_symbol_canonicalization_examples(raw: str, expected: str):
    result = canonicalize_symbol(raw)

    assert result.canonical_symbol == expected
    assert result.status == "ok"
