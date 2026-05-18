from __future__ import annotations

from pathlib import Path

from market_price_guard.main import EXIT_OK, EXIT_STRICT_BLOCKED, PROJECT_ROOT, run_pipeline


def test_profile_energy_generates_index(tmp_path):
    output_dir = tmp_path / "energy"

    result = run_pipeline(output_dir=output_dir, provider_mode="mock", profile="energy", strict=True)
    index = (output_dir / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_OK
    assert "# market_price_guard 本轮刷新索引" in index
    assert "profile: energy" in index
    assert "energy_price_block.md" in index


def test_profile_tech_generates_index(tmp_path):
    output_dir = tmp_path / "tech"

    result = run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)
    index = (output_dir / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_OK
    assert "profile: tech" in index
    assert "tech_price_block.md" in index


def test_profile_all_generates_index(tmp_path):
    output_dir = tmp_path / "all"

    result = run_pipeline(output_dir=output_dir, provider_mode="mock", profile="all", strict=True)
    index = (output_dir / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == EXIT_OK
    assert "profile: all" in index
    assert "controller_price_summary.md" in index


def test_index_contains_basic_fields_and_report_links(tmp_path):
    output_dir = tmp_path / "out"

    result = run_pipeline(output_dir=output_dir, provider_mode="mock", provider_policy="fast", profile="energy", strict=True)
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


def test_strict_blocked_index_contains_blocking_summary(tmp_path):
    stale_rules = _write_stale_rules(tmp_path, default_max_age=900, manual_max_age=1)
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


def test_scripts_exist_and_use_expected_arguments():
    scripts_dir = PROJECT_ROOT / "scripts"
    expected = {
        "run_energy_fast_strict.ps1": ["--profile energy", "--provider-policy fast", "--strict", "outputs_energy_latest"],
        "run_tech_fast_strict.ps1": ["--profile tech", "--provider-policy fast", "--strict", "outputs_tech_latest"],
        "run_all_fast_strict.ps1": ["--profile all", "--provider-policy fast", "--strict", "outputs_all_latest"],
        "run_diagnostic.ps1": ["--profile all", "--provider-policy diagnostic", "outputs_diagnostic"],
        "run_mock_strict.ps1": ["--provider-mode mock", "--strict", "outputs_mock_latest"],
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


def _write_stale_rules(tmp_path: Path, default_max_age: int, manual_max_age: int) -> Path:
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
