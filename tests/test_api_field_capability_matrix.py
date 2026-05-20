from __future__ import annotations

from pathlib import Path


DOC = Path("docs/api_field_capability_matrix.md")


def test_api_field_capability_matrix_exists_and_has_main_table():
    content = DOC.read_text(encoding="utf-8")

    assert "# API Field Capability Matrix" in content
    assert "| Field | Priority | Current support status | API native support | Calculable from existing fields |" in content


def test_api_field_capability_matrix_has_priorities_and_providers():
    content = DOC.read_text(encoding="utf-8")

    for text in ["P0", "P1", "P2", "akshare", "eastmoney_direct", "yfinance", "manual", "mock"]:
        assert text in content


def test_api_field_capability_matrix_covers_key_future_gaps():
    content = DOC.read_text(encoding="utf-8")

    for field in ["minute_bars", "intraday_vwap", "premium_pct", "allowed_advice_level", "operation_permission"]:
        assert field in content
    assert "minute_bars / VWAP are not developed" in content
    assert "QDII premium is not developed" in content
    assert "not API native" in content
    assert "preferred_action" in content


def test_known_issues_include_market_exchange_and_future_gaps():
    content = Path("docs/known_issues.md").read_text(encoding="utf-8")

    assert "market == \"CN\"" in content
    assert "exchange=SH/SZ/HK/US" in content
    assert "Eastmoney Direct remains unstable" in content
    assert "minute_bars" in content
    assert "QDII premium" in content


def test_readme_references_api_field_capability_matrix():
    content = Path("README.md").read_text(encoding="utf-8")

    assert "docs/api_field_capability_matrix.md" in content
    assert "v0.7.1.4 base quote field normalization" in content
