from __future__ import annotations

import pandas as pd
import time
from datetime import datetime, timedelta, timezone

from market_price_guard.main import EXIT_OK, EXIT_STRICT_BLOCKED, PROJECT_ROOT, main, run_pipeline
from market_price_guard.providers.akshare_provider import AkshareProvider
from market_price_guard.providers.mock_provider import MockProvider


def test_default_arguments_can_run(tmp_path):
    result = run_pipeline(output_dir=tmp_path)

    assert result.exit_code == EXIT_OK
    assert (tmp_path / "prices_snapshot.csv").exists()


def test_custom_output_dir_generates_files(tmp_path):
    output_dir = tmp_path / "custom_outputs"

    result = run_pipeline(output_dir=output_dir)

    assert result.exit_code == EXIT_OK
    assert (output_dir / "data_completeness_report.md").exists()
    assert (output_dir / "provider_health_report.md").exists()
    assert (output_dir / "runtime_diagnostics.md").exists()
    assert (output_dir / "controller_price_summary.md").exists()


def test_non_strict_stale_data_does_not_fail(tmp_path):
    stale_rules = _write_stale_rules(tmp_path, default_max_age=1, manual_max_age=1)

    result = run_pipeline(stale_rules_path=stale_rules, output_dir=tmp_path / "out", strict=False)

    assert result.exit_code == EXIT_OK
    assert result.completeness.usable_for_operation is False


def test_required_stale_record_causes_exit_code_2(tmp_path):
    stale_rules = _write_stale_rules(tmp_path, default_max_age=900, manual_max_age=1)

    result = run_pipeline(stale_rules_path=stale_rules, output_dir=tmp_path / "out", strict=True)

    assert result.exit_code == EXIT_STRICT_BLOCKED


def test_quote_time_missing_is_reported(tmp_path):
    watchlist = tmp_path / "watchlist.yaml"
    stale_rules = tmp_path / "stale_rules.yaml"
    mock_prices = tmp_path / "mock_prices.yaml"
    output_dir = tmp_path / "out"
    watchlist.write_text(
        """
projects:
  energy:
    display_name: "energy"
    allow_full_detail: true
    instruments:
      - symbol: "00883.HK"
        name: "中海油H"
        market: "HK"
        core: true
        provider: "mock"
        required_for_operation: true
""".strip(),
        encoding="utf-8",
    )
    stale_rules.write_text(
        """
default:
  max_age_seconds_open: 900
  max_age_seconds_closed: 86400
manual:
  max_age_seconds: 604800
markets: {}
""".strip(),
        encoding="utf-8",
    )
    mock_prices.write_text(
        """
prices:
  - symbol: "00883.HK"
    price: 21.35
    currency: "HKD"
    source: "mock"
    fetch_time: "2026-05-18T12:50:00+08:00"
    market_status: "closed"
""".strip(),
        encoding="utf-8",
    )

    result = run_pipeline(
        watchlist_path=watchlist,
        stale_rules_path=stale_rules,
        mock_prices_path=mock_prices,
        output_dir=output_dir,
        strict=True,
    )
    report = (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_STRICT_BLOCKED
    assert "quote_time_missing" in report


def test_readme_contains_strict_mode_description():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "strict 模式" in readme
    assert "exit code 2" in readme


def test_gold_stale_non_strict_reports_but_exits_zero(tmp_path):
    stale_rules = _write_stale_rules(tmp_path, default_max_age=900, manual_max_age=1)

    result = run_pipeline(stale_rules_path=stale_rules, output_dir=tmp_path / "out", strict=False)
    report = (tmp_path / "out" / "data_completeness_report.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_OK
    assert "GOLD_CNY" in report
    assert "不可用于具体操作建议" in report


def test_gold_stale_strict_returns_exit_code_2(tmp_path):
    stale_rules = _write_stale_rules(tmp_path, default_max_age=900, manual_max_age=1)

    result = run_pipeline(stale_rules_path=stale_rules, output_dir=tmp_path / "out", strict=True)

    assert result.exit_code == EXIT_STRICT_BLOCKED
    assert any(record["symbol"] == "GOLD_CNY" for record in result.completeness.strict_blockers)


def test_non_required_stale_record_does_not_cause_exit_code_2(tmp_path):
    watchlist = tmp_path / "watchlist.yaml"
    mock_prices = tmp_path / "mock_prices.yaml"
    stale_rules = _write_stale_rules(tmp_path, default_max_age=1, manual_max_age=604800)
    watchlist.write_text(
        """
projects:
  tech:
    display_name: "tech"
    allow_full_detail: true
    instruments:
      - symbol: "510300.SH"
        name: "沪深300ETF"
        market: "CN"
        core: false
        provider: "mock"
        required_for_operation: false
        asset_role: "non_tech_broad_base_etf"
""".strip(),
        encoding="utf-8",
    )
    mock_prices.write_text(
        """
prices:
  - symbol: "510300.SH"
    price: 3.921
    currency: "CNY"
    source: "mock"
    quote_time: "2026-05-18T12:45:00+08:00"
    fetch_time: "2026-05-18T12:50:00+08:00"
    market_status: "closed"
""".strip(),
        encoding="utf-8",
    )

    result = run_pipeline(
        watchlist_path=watchlist,
        mock_prices_path=mock_prices,
        stale_rules_path=stale_rules,
        output_dir=tmp_path / "out",
        strict=True,
    )
    report = (tmp_path / "out" / "data_completeness_report.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_OK
    assert not any(record["symbol"] == "510300.SH" for record in result.completeness.strict_blockers)
    assert "warning" in report


def test_provider_mode_mock_does_not_call_akshare(monkeypatch, tmp_path):
    def fail_fetch(self, symbols):
        raise AssertionError("AKShare should not be called in mock mode")

    monkeypatch.setattr(AkshareProvider, "fetch", fail_fetch)

    result = run_pipeline(output_dir=tmp_path / "out", provider_mode="mock")

    assert result.exit_code == EXIT_OK


def test_provider_mode_live_can_be_monkeypatched_without_network(monkeypatch, tmp_path):
    def fake_fetch(self, symbols):
        return {
            symbol: _fake_akshare_raw(symbol, price=1.0 + index)
            for index, symbol in enumerate(symbols)
        }

    monkeypatch.setattr(AkshareProvider, "fetch", fake_fetch)

    result = run_pipeline(output_dir=tmp_path / "out", provider_mode="live", provider_policy="conservative", strict=True)
    df = pd.read_csv(tmp_path / "out" / "prices_snapshot.csv")

    assert result.exit_code == EXIT_OK
    assert set(df[df["symbol"].isin(["601899.SH", "159819.SZ"])]["source"]) == {"akshare"}
    assert df[df["symbol"] == "GOLD_CNY"]["source"].iloc[0] == "manual"


def test_gold_quote_time_missing_is_reported(tmp_path):
    manual_prices = tmp_path / "manual_prices.yaml"
    manual_prices.write_text(_manual_gold_yaml(quote_time_line=""), encoding="utf-8")

    result = run_pipeline(manual_prices_path=manual_prices, output_dir=tmp_path / "out", strict=True)
    report = (tmp_path / "out" / "data_completeness_report.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_STRICT_BLOCKED
    assert "quote_time_missing" in report


def test_gold_invalid_price_is_reported(tmp_path):
    manual_prices = tmp_path / "manual_prices.yaml"
    manual_prices.write_text(_manual_gold_yaml(price="-1"), encoding="utf-8")

    result = run_pipeline(manual_prices_path=manual_prices, output_dir=tmp_path / "out", strict=True)
    report = (tmp_path / "out" / "data_completeness_report.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_STRICT_BLOCKED
    assert "invalid_price" in report


def test_readme_contains_manual_prices_and_gold_manual_description():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "manual_prices.yaml" in readme
    assert "黄金持仓参考价" in readme
    assert "不等同于国际现货金价" in readme


def test_strict_failure_output_and_report_include_blocking_symbol(tmp_path, capsys):
    stale_rules = _write_stale_rules(tmp_path, default_max_age=900, manual_max_age=1)
    output_dir = tmp_path / "out"

    exit_code = main(["--strict", "--stale-rules", str(stale_rules), "--output-dir", str(output_dir)])
    captured = capsys.readouterr()
    report = (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")

    assert exit_code == EXIT_STRICT_BLOCKED
    assert "Strict mode blocked operation because the following required prices are not usable:" in captured.err
    assert "GOLD_CNY" in captured.err
    assert "Strict blocking records" in report
    assert "GOLD_CNY" in report


def test_provider_health_report_does_not_change_strict_exit_code(tmp_path):
    stale_rules = _write_stale_rules(tmp_path, default_max_age=900, manual_max_age=1)

    result = run_pipeline(stale_rules_path=stale_rules, output_dir=tmp_path / "out", strict=True)

    assert result.exit_code == EXIT_STRICT_BLOCKED
    assert (tmp_path / "out" / "provider_health_report.md").exists()


def test_profile_tech_only_contains_tech_symbols(tmp_path):
    result = run_pipeline(output_dir=tmp_path / "out", provider_mode="mock", profile="tech", strict=True, mock_prices_path=_fresh_mock_prices(tmp_path), manual_prices_path=_fresh_manual_prices(tmp_path))
    df = pd.read_csv(tmp_path / "out" / "prices_snapshot.csv")

    assert result.exit_code == EXIT_OK
    assert set(df["symbol"]) == {"159632.SZ", "513300.SH", "159819.SZ", "159516.SZ", "515880.SH", "510300.SH", "GOLD_CNY"}


def test_profile_energy_only_contains_energy_symbols(tmp_path):
    result = run_pipeline(output_dir=tmp_path / "out", provider_mode="mock", profile="energy", strict=True, mock_prices_path=_fresh_mock_prices(tmp_path))
    df = pd.read_csv(tmp_path / "out" / "prices_snapshot.csv")

    assert result.exit_code == EXIT_OK
    assert set(df["symbol"]) == {"00883.HK", "601899.SH", "601985.SH", "003816.SZ"}


def test_profile_all_keeps_full_watchlist(tmp_path):
    result = run_pipeline(output_dir=tmp_path / "out", provider_mode="mock", profile="all")
    df = pd.read_csv(tmp_path / "out" / "prices_snapshot.csv")

    assert result.exit_code == EXIT_OK
    assert len(df) == 14


def test_runtime_diagnostics_contains_core_fields(tmp_path):
    result = run_pipeline(output_dir=tmp_path / "out", provider_mode="mock", profile="controller")
    report = (tmp_path / "out" / "runtime_diagnostics.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_OK
    assert "total_elapsed_seconds" in report
    assert "profile: controller" in report
    assert "provider_mode: mock" in report
    assert "provider_policy: fast" in report


def test_reports_include_provider_policy(tmp_path):
    run_pipeline(output_dir=tmp_path / "out", provider_mode="mock", provider_policy="diagnostic", profile="controller")
    health = (tmp_path / "out" / "provider_health_report.md").read_text(encoding="utf-8")
    completeness = (tmp_path / "out" / "data_completeness_report.md").read_text(encoding="utf-8")
    runtime = (tmp_path / "out" / "runtime_diagnostics.md").read_text(encoding="utf-8")

    assert "provider_policy=diagnostic" in health
    assert "provider_policy: diagnostic" in completeness
    assert "provider_policy: diagnostic" in runtime


def test_provider_health_report_attempts_include_elapsed_seconds(tmp_path):
    run_pipeline(output_dir=tmp_path / "out", provider_mode="mock", profile="energy")
    report = (tmp_path / "out" / "provider_health_report.md").read_text(encoding="utf-8")

    assert "elapsed_seconds=" in report


def test_slow_provider_attempt_is_reported(monkeypatch, tmp_path):
    original_fetch = MockProvider.fetch

    def slow_fetch(self, symbols):
        time.sleep(0.02)
        return original_fetch(self, symbols)

    monkeypatch.setattr(MockProvider, "fetch", slow_fetch)

    run_pipeline(output_dir=tmp_path / "out", provider_mode="mock", profile="energy", timeout_seconds=0.001)
    runtime_report = (tmp_path / "out" / "runtime_diagnostics.md").read_text(encoding="utf-8")
    health_report = (tmp_path / "out" / "provider_health_report.md").read_text(encoding="utf-8")

    assert "slow_provider_attempts" in runtime_report
    assert "slow_provider_attempt=True" in health_report


def test_runtime_diagnostics_include_provider_budget_counts(tmp_path):
    run_pipeline(output_dir=tmp_path / "out", provider_mode="mock", profile="energy")
    runtime_report = (tmp_path / "out" / "runtime_diagnostics.md").read_text(encoding="utf-8")

    assert "provider_runtime_budget" in runtime_report
    assert "provider_skipped_by_runtime_budget_count" in runtime_report
    assert "slow_provider_attempts_count" in runtime_report
    assert "## Cache / Reuse Summary" in runtime_report
    assert "quote_cache_hit_count" in runtime_report
    assert "repeated_provider_call_prevented_count" in runtime_report


def test_run_time_budget_exceeded_appears_in_completeness_report(tmp_path):
    run_pipeline(output_dir=tmp_path / "out", provider_mode="mock", profile="controller", max_run_seconds=0)
    report = (tmp_path / "out" / "data_completeness_report.md").read_text(encoding="utf-8")

    assert "run_time_budget_exceeded: True" in report
    assert "本轮刷新耗时超过预算" in report


def test_profile_tech_ignores_energy_strict_failures(monkeypatch, tmp_path):
    def fail_fetch(self, symbols):
        raise AssertionError("AKShare should not be called for energy in tech profile")

    monkeypatch.setattr(AkshareProvider, "fetch", fail_fetch)

    result = run_pipeline(output_dir=tmp_path / "out", provider_mode="mock", profile="tech", strict=True, mock_prices_path=_fresh_mock_prices(tmp_path), manual_prices_path=_fresh_manual_prices(tmp_path))

    assert result.exit_code == EXIT_OK


def test_profile_energy_ignores_tech_strict_failures(tmp_path):
    result = run_pipeline(output_dir=tmp_path / "out", provider_mode="mock", profile="energy", strict=True, mock_prices_path=_fresh_mock_prices(tmp_path))
    df = pd.read_csv(tmp_path / "out" / "prices_snapshot.csv")

    assert result.exit_code == EXIT_OK
    assert "GOLD_CNY" not in set(df["symbol"])
    assert "159819.SZ" not in set(df["symbol"])


def _write_stale_rules(tmp_path, default_max_age: int, manual_max_age: int):
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


def _fresh_mock_prices(tmp_path):
    path = tmp_path / "fresh_mock_prices.yaml"
    content = (PROJECT_ROOT / "config" / "mock_prices.yaml").read_text(encoding="utf-8")
    now = datetime.now(timezone(timedelta(hours=8)))
    quote_time = (now - timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    fetch_time = now.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    path.write_text(
        content.replace("2026-05-20T12:45:00+08:00", quote_time).replace("2026-05-20T12:50:00+08:00", fetch_time),
        encoding="utf-8",
    )
    return path


def _fresh_manual_prices(tmp_path):
    path = tmp_path / "fresh_manual_prices.yaml"
    quote_time = (datetime.now(timezone(timedelta(hours=8))) - timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    path.write_text(_manual_gold_yaml(quote_time_line=f'    quote_time: "{quote_time}"'), encoding="utf-8")
    return path


def _manual_gold_yaml(price: str = "1040.0", quote_time_line: str = '    quote_time: "2026-05-18T09:30:00+08:00"'):
    return f"""
manual_prices:
  - symbol: "GOLD_CNY"
    name: "黄金持仓参考价"
    market: "MANUAL"
    price: {price}
    currency: "CNY"
{quote_time_line}
    source: "manual"
    source_note: "用户手工录入"
    product_type: "gold_savings_or_gold_wealth_product"
    price_type: "estimated_sellable_or_valuation_price"
    tradable: true
    fee_note: "手续费、点差、赎回到账规则未自动计算"
    project: "tech"
    asset_role: "defense_or_potential_tech_funding"
    is_core: true
    required_for_operation: true
""".strip()


def _fake_akshare_raw(symbol: str, price: float):
    from market_price_guard.freshness import now_utc
    from market_price_guard.models import RawPrice

    now = now_utc()
    return RawPrice(
        symbol=symbol,
        price=price,
        currency="HKD" if symbol.endswith(".HK") else "CNY",
        source="akshare",
        quote_time=now,
        fetch_time=now,
        market_status="open",
    )
