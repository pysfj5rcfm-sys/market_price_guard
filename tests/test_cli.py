from __future__ import annotations

from pathlib import Path

from market_price_guard.main import EXIT_OK, EXIT_STRICT_BLOCKED, PROJECT_ROOT, run_pipeline


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
    stale_rules = tmp_path / "stale_rules.yaml"
    stale_rules.write_text(
        """
default:
  max_age_seconds_open: 1
  max_age_seconds_closed: 1
manual:
  max_age_seconds: 1
markets: {}
""".strip(),
        encoding="utf-8",
    )

    result = run_pipeline(stale_rules_path=stale_rules, output_dir=tmp_path / "out", strict=False)

    assert result.exit_code == EXIT_OK
    assert result.completeness.usable_for_operation is False


def test_strict_core_stale_data_returns_exit_code_2(tmp_path):
    stale_rules = tmp_path / "stale_rules.yaml"
    stale_rules.write_text(
        """
default:
  max_age_seconds_open: 1
  max_age_seconds_closed: 1
manual:
  max_age_seconds: 1
markets: {}
""".strip(),
        encoding="utf-8",
    )

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
manual_prices: []
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
