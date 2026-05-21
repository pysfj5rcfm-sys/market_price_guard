from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from market_price_guard.main import EXIT_OK, parse_args, run_pipeline
from market_price_guard.models import RawPrice
from market_price_guard.providers.akshare_provider import AkshareProvider
from market_price_guard.providers.eastmoney_direct_provider import EastmoneyDirectProvider
from market_price_guard.providers.yfinance_provider import YFinanceProvider
from market_price_guard.report import get_blocking_records


ETF_SYMBOLS = ["159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"]
TECH_CORE_SYMBOLS = [*ETF_SYMBOLS, "159516.SZ"]


def test_quote_purpose_cli_defaults_to_operation_and_accepts_reference():
    assert parse_args([]).quote_purpose == "operation"
    assert parse_args(["--quote-purpose", "reference"]).quote_purpose == "reference"


def test_tech_reference_script_contract():
    script = _script("run_tech_fast_reference.ps1")
    strict_script = _script("run_tech_fast_strict.ps1")

    assert "--profile tech" in script
    assert "--provider-mode live" in script
    assert "--provider-policy fast" in script
    assert "--quote-purpose reference" in script
    assert "--output-dir outputs_tech_reference_latest" in script
    assert "--strict" not in script
    assert "D:\\AIProjects\\market_price_guard" not in script
    assert "`" not in script
    assert "“" not in script and "”" not in script
    assert "--quote-purpose reference" not in strict_script
    assert "outputs_tech_latest" in strict_script


def test_reference_mode_uses_eastmoney_for_tech_etfs_and_skips_slower_sources(monkeypatch, tmp_path):
    calls = {"eastmoney": 0, "yfinance": 0, "akshare": 0}

    def eastmoney_fetch(self, symbols):
        calls["eastmoney"] += 1
        return {
            symbol: _raw(symbol, source="eastmoney_direct", price=1.0 + index / 100)
            for index, symbol in enumerate(symbols)
            if symbol in ETF_SYMBOLS
        }

    def yfinance_fetch(self, symbols):
        calls["yfinance"] += 1
        return {
            symbol: _raw(symbol, source="yfinance", price=1.0 + index / 100)
            for index, symbol in enumerate(symbols)
            if symbol in ETF_SYMBOLS
        }

    def akshare_fetch(self, symbols):
        calls["akshare"] += 1
        return {symbol: _raw(symbol, source="akshare", price=2.0 + index / 100) for index, symbol in enumerate(symbols) if symbol in TECH_CORE_SYMBOLS}

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
    etf_rows = df[df["symbol"].isin(ETF_SYMBOLS)]
    index = (output_dir / "index.md").read_text(encoding="utf-8")
    health = (output_dir / "provider_health_report.md").read_text(encoding="utf-8")
    completeness = (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_OK
    assert calls["eastmoney"] == len(ETF_SYMBOLS)
    assert calls["yfinance"] == len(ETF_SYMBOLS)
    assert calls["akshare"] == 1
    assert set(etf_rows["selected_provider"]) == {"eastmoney_direct"}
    assert set(etf_rows["quote_purpose"]) == {"reference"}
    assert set(etf_rows["quote_trust_tier"]) == {"reference"}
    assert set(etf_rows["usable_for_reference"].astype(str)) == {"True"}
    assert set(etf_rows["usable_for_operation"].astype(str)) == {"False"}
    assert set(etf_rows["confirmation_required"].astype(str)) == {"True"}
    assert "可用于具体操作建议：否" in index
    assert "可用于快速参考：是" in index
    assert "operation confirmation required" in completeness
    assert "not official exchange" in completeness
    assert "effective_provider_chain: eastmoney_direct, yfinance, akshare, mock" in health
    assert "selected_provider: eastmoney_direct" in health
    assert "skipped because eastmoney_direct reference quote succeeded in reference mode" in health
    assert "price_reconciliation_report.md" in completeness
    assert not (output_dir / "energy_price_block.md").exists()
    assert not (output_dir / "controller_price_summary.md").exists()
    assert (output_dir / "tech_price_block.md").exists()


def test_operation_tech_path_keeps_akshare_first(monkeypatch, tmp_path):
    calls = {"akshare": 0, "yfinance": 0}

    def yfinance_fetch(self, symbols):
        calls["yfinance"] += 1
        raise AssertionError("operation tech path should not call yfinance before AKShare")

    def akshare_fetch(self, symbols):
        calls["akshare"] += 1
        return {symbol: _raw(symbol, source="akshare", price=2.0 + index / 100) for index, symbol in enumerate(symbols) if symbol in TECH_CORE_SYMBOLS}

    monkeypatch.setattr(YFinanceProvider, "fetch", yfinance_fetch)
    monkeypatch.setattr(AkshareProvider, "fetch", akshare_fetch)

    output_dir = tmp_path / "tech_operation"
    result = run_pipeline(
        output_dir=output_dir,
        provider_mode="live",
        provider_policy="fast",
        profile="tech",
        quote_purpose="operation",
        strict=True,
    )
    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")
    etf_rows = df[df["symbol"].isin(ETF_SYMBOLS)]

    assert result.exit_code == EXIT_OK
    assert calls["yfinance"] == 0
    assert set(etf_rows["selected_provider"]) == {"akshare"}
    assert set(etf_rows["quote_purpose"]) == {"operation"}
    assert set(etf_rows["quote_trust_tier"]) == {"operation"}
    assert not (output_dir / "energy_price_block.md").exists()
    assert not (output_dir / "controller_price_summary.md").exists()


def test_yfinance_etf_reference_grade_does_not_pass_operation_blocking_rules():
    from market_price_guard.normalize import load_watchlist, load_yaml, normalize_records

    records = normalize_records(
        load_watchlist(__import__("pathlib").Path("config/watchlist.yaml")),
        {"159819.SZ": _raw("159819.SZ", source="yfinance")},
        load_yaml(__import__("pathlib").Path("config/stale_rules.yaml")),
        now=datetime.now(timezone.utc),
    )
    record = next(item for item in records if item.symbol == "159819.SZ")

    assert record.quote_trust_tier == "reference"
    assert record.usable_for_operation is False
    assert get_blocking_records([record])[0]["blocking_reason"] == "reference_tier_requires_operation_confirmation"


def _raw(symbol: str, source: str = "yfinance", price: float = 1.23) -> RawPrice:
    quote_time = datetime.now(timezone.utc)
    return RawPrice(
        symbol=symbol,
        name=symbol,
        market="CN",
        price=price,
        currency="CNY",
        source=source,
        quote_time=quote_time,
        fetch_time=quote_time,
        market_status="open",
        provider_diagnostics={"selected_provider": source, "provider": source, "function_name": f"{source}.mock"},
    )


def _script(name: str) -> str:
    from market_price_guard.main import PROJECT_ROOT

    return (PROJECT_ROOT / "scripts" / name).read_text(encoding="utf-8")
