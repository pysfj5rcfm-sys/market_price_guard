from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from market_price_guard.main import EXIT_OK, EXIT_STRICT_BLOCKED, PROJECT_ROOT, run_pipeline


@pytest.mark.parametrize("profile", ["energy", "tech", "all"])
def test_profile_generates_index_with_upload_bundle_first(tmp_path, profile):
    output_dir = tmp_path / profile

    result = run_pipeline(
        output_dir=output_dir,
        provider_mode="mock",
        profile=profile,
        strict=True,
        mock_prices_path=_fresh_mock_prices(tmp_path),
        manual_prices_path=_fresh_manual_prices(tmp_path),
    )
    index = (output_dir / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_OK
    assert "# market_price_guard 本轮刷新索引" in index
    assert f"profile: {profile}" in index
    assert "0_upload_bundle.md" in index
    assert "debug_bundle.md if blocking" in index


def test_index_contains_basic_fields_and_report_links(tmp_path):
    output_dir = tmp_path / "out"

    result = run_pipeline(output_dir=output_dir, provider_mode="mock", provider_policy="fast", profile="energy", strict=True, mock_prices_path=_fresh_mock_prices(tmp_path))
    index = (output_dir / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_OK
    assert "generated_at:" in index
    assert "provider_mode: mock" in index
    assert "provider_policy: fast" in index
    assert "strict: true" in index
    assert "exit_code: 0" in index
    assert "data_completeness_report.md" in index
    assert "provider_health_report.md" in index
    assert "runtime_diagnostics.md" in index
    assert "可用于具体操作建议：是" in index


def test_strict_blocked_index_contains_blocking_summary(tmp_path, stale_rules_factory):
    stale_rules = stale_rules_factory(default_max_age=900, manual_max_age=1)
    output_dir = tmp_path / "blocked"

    result = run_pipeline(
        stale_rules_path=stale_rules,
        output_dir=output_dir,
        provider_mode="mock",
        profile="tech",
        strict=True,
    )
    index = (output_dir / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_STRICT_BLOCKED
    assert "可用于具体操作建议：否" in index
    assert "## Blocking Records 摘要" in index
    assert "GOLD_CNY" in index
    assert "strict blocking records 数量:" in index


def test_index_utf8_readable_and_no_investment_action_terms(tmp_path):
    output_dir = tmp_path / "out"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="all", strict=True)
    index = (output_dir / "index.md").read_text(encoding="utf-8")

    for forbidden in ["买入", "卖出", "加仓", "减仓", "做T", "目标价"]:
        assert forbidden not in index


@pytest.mark.script
def test_scripts_exist_and_use_expected_arguments():
    scripts_dir = PROJECT_ROOT / "scripts"
    expected = {
        "run_energy_fast_strict.ps1": ["--profile energy", "--provider-policy fast", "--strict", "outputs_energy_latest"],
        "run_tech_fast_strict.ps1": ["--profile tech", "--provider-policy fast", "--strict", "outputs_tech_latest"],
        "run_all_fast_strict.ps1": ["--profile all", "--provider-policy fast", "--strict", "outputs_all_latest"],
        "run_diagnostic.ps1": ["--profile all", "--provider-policy diagnostic", "outputs_diagnostic"],
        "run_mock_strict.ps1": ["--provider-mode mock", "--strict", "outputs_mock_latest"],
        "run_tech_fast_reference.ps1": ["--profile tech", "--provider-policy fast", "--quote-purpose reference", "outputs_tech_reference_latest"],
        "run_tech_reconcile.ps1": ["--profile tech", "--provider-policy diagnostic", "--quote-purpose reference", "--reconcile-mode full", "outputs_tech_reconcile_latest"],
    }

    assert scripts_dir.exists()
    for filename, snippets in expected.items():
        script = scripts_dir / filename
        content = script.read_text(encoding="utf-8")
        assert script.exists()
        assert "D:\\AIProjects\\market_price_guard" not in content
        assert "“" not in content
        assert "”" not in content
        assert "`" not in content
        assert "$MyInvocation.MyCommand.Path" in content
        assert ".venv\\Scripts\\python.exe" in content
        for snippet in snippets:
            assert snippet in content
    reference_content = (scripts_dir / "run_tech_fast_reference.ps1").read_text(encoding="utf-8")
    assert "--strict" not in reference_content
    assert "--strict" not in (scripts_dir / "run_tech_reconcile.ps1").read_text(encoding="utf-8")
    assert "--quote-purpose reference" not in (scripts_dir / "run_tech_fast_strict.ps1").read_text(encoding="utf-8")


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
    path.write_text(
        f"""
manual_prices:
  - symbol: "GOLD_CNY"
    name: "黄金持仓参考价"
    market: "MANUAL"
    price: 1040.0
    currency: "CNY"
    quote_time: "{quote_time}"
    source: "manual"
    source_note: "用户手工录入"
    product_type: "gold_savings_or_gold_wealth_product"
    price_type: "estimated_sellable_or_valuation_price"
    tradable: true
    project: "tech"
    asset_role: "defense_or_potential_tech_funding"
    is_core: true
    required_for_operation: true
""".strip(),
        encoding="utf-8",
    )
    return path
