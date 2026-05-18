from __future__ import annotations

from market_price_guard.main import EXIT_OK, EXIT_STRICT_BLOCKED, PROJECT_ROOT, main, run_pipeline


def test_default_arguments_can_run(tmp_path):
    result = run_pipeline(output_dir=tmp_path)

    assert result.exit_code == EXIT_OK
    assert (tmp_path / "prices_snapshot.csv").exists()


def test_custom_output_dir_generates_files(tmp_path):
    output_dir = tmp_path / "custom_outputs"

    result = run_pipeline(output_dir=output_dir)

    assert result.exit_code == EXIT_OK
    assert (output_dir / "data_completeness_report.md").exists()
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
    stale_rules = _write_stale_rules(tmp_path, default_max_age=1, manual_max_age=604800)

    result = run_pipeline(stale_rules_path=stale_rules, output_dir=tmp_path / "out", strict=True)
    report = (tmp_path / "out" / "data_completeness_report.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_OK
    assert result.completeness.strict_blockers == []
    assert "warning" in report


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
