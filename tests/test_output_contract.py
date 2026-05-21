from __future__ import annotations

import pandas as pd
import pytest

from market_price_guard.main import PROJECT_ROOT, run_pipeline
from market_price_guard.report import TECH_GROUPS


def test_contract_docs_exist_and_describe_outputs():
    output_contract = (PROJECT_ROOT / "docs" / "output_contract.md").read_text(encoding="utf-8")
    uat_checklist = (PROJECT_ROOT / "docs" / "uat_checklist.md").read_text(encoding="utf-8")

    assert "index.md" in output_contract
    assert "tech_price_block.md" in output_contract
    assert "prices_snapshot.csv" in output_contract
    assert "run_tech_fast_strict.ps1" in uat_checklist
    assert "strict=2" in uat_checklist


def test_index_contract_fields_and_links(tmp_path):
    output_dir = tmp_path / "energy"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="energy", strict=True)
    index = (output_dir / "index.md").read_text(encoding="utf-8")

    for expected in [
        "generated_at:",
        "profile: energy",
        "provider_mode: mock",
        "provider_policy: fast",
        "strict: true",
        "exit_code:",
        "output_dir:",
        "data_completeness_report.md",
        "provider_health_report.md",
        "runtime_diagnostics.md",
    ]:
        assert expected in index


def test_strict_blocked_index_contract_has_blocking_summary(tmp_path, stale_rules_factory):
    stale_rules = stale_rules_factory(default_max_age=900, manual_max_age=1)
    output_dir = tmp_path / "blocked"

    run_pipeline(
        stale_rules_path=stale_rules,
        output_dir=output_dir,
        provider_mode="mock",
        profile="tech",
        strict=True,
    )
    index = (output_dir / "index.md").read_text(encoding="utf-8")

    assert "Blocking Records" in index
    assert "GOLD_CNY" in index
    assert "blocking_reason" in index


def test_tech_price_block_contract_grouping(tmp_path):
    output_dir = tmp_path / "tech"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)
    report = (output_dir / "tech_price_block.md").read_text(encoding="utf-8")
    group_titles = [title for title, _asset_role in TECH_GROUPS]

    for title in group_titles:
        assert title in report

    nasdaq = _section(report, group_titles[0], group_titles[1])
    ai = _section(report, group_titles[1], group_titles[2])
    communication = _section(report, group_titles[2], group_titles[3])
    gold = _section(report, group_titles[3], group_titles[4])
    broad = report.split(f"## {group_titles[4]}", 1)[1]

    assert "159632.SZ" in nasdaq
    assert "513300.SH" in nasdaq
    assert "159819.SZ" in ai
    assert "515880.SH" in communication
    assert "GOLD_CNY" in gold
    assert "510300.SH" in broad
    assert "GOLD_CNY" not in nasdaq + ai + communication
    assert "510300.SH" not in nasdaq + ai + communication


def test_energy_price_block_contract_core_symbols(tmp_path):
    output_dir = tmp_path / "energy"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="energy", strict=True)
    report = (output_dir / "energy_price_block.md").read_text(encoding="utf-8")

    for symbol in ["00883.HK", "601899.SH", "601985.SH", "003816.SZ"]:
        assert symbol in report
    for field in ["source", "quote_time", "is_stale", "stale_reason"]:
        assert field in report


def test_controller_summary_contract_is_summary_only(tmp_path):
    output_dir = tmp_path / "all"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="all", strict=True)
    report = (output_dir / "controller_price_summary.md").read_text(encoding="utf-8")

    assert "00883.HK" not in report
    assert "601899.SH" not in report
    assert "Provider attempts by symbol" not in report
    assert "GOLD_CNY" not in report


def test_prices_snapshot_contract_current_stable_columns(tmp_path):
    output_dir = tmp_path / "all"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="all", strict=True)
    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")

    for column in [
        "project",
        "symbol",
        "name",
        "market",
        "price",
        "currency",
        "source",
        "quote_time",
        "fetch_time",
        "market_status",
        "is_stale",
        "stale_reason",
    ]:
        assert column in df.columns


def test_provider_health_and_runtime_contract(tmp_path):
    output_dir = tmp_path / "all"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="all", strict=True)
    health = (output_dir / "provider_health_report.md").read_text(encoding="utf-8")
    runtime = (output_dir / "runtime_diagnostics.md").read_text(encoding="utf-8")

    for expected in ["provider_policy", "selected_provider", "fallback_used", "usable_for_operation", "attempts"]:
        assert expected in health
    for expected in ["total_elapsed_seconds", "profile", "provider_mode", "provider_policy", "run_time_budget_exceeded"]:
        assert expected in runtime


def test_generated_markdown_has_no_actionable_advice_phrases(tmp_path):
    output_dir = tmp_path / "all"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="all", strict=True)
    forbidden = ["建议买", "建议卖", "建议买入", "建议卖出", "建议加仓", "建议减仓", "目标价"]

    for markdown in output_dir.glob("*.md"):
        content = markdown.read_text(encoding="utf-8")
        for phrase in forbidden:
            assert phrase not in content


@pytest.mark.uat
def test_run_uat_script_contract():
    script = (PROJECT_ROOT / "scripts" / "run_uat.ps1").read_text(encoding="utf-8")

    assert "D:\\AIProjects\\market_price_guard" not in script
    assert "“" not in script
    assert "”" not in script
    assert "`" not in script
    for script_name in [
        "run_tech_fast_strict.ps1",
        "run_energy_fast_strict.ps1",
        "run_all_fast_strict.ps1",
        "run_tech_reconcile.ps1",
        "run_diagnostic.ps1",
    ]:
        assert script_name in script
    assert "strict_blocked_but_reported" in script
    assert "-Mode quick" not in script
    assert "$Mode = 'quick'" in script
    assert "skipped_by_profile" in script
    assert "total_defined" in script
    assert "run_count" in script
    assert "tech_minute_probe" in script
    assert "[switch]$UseRunCache" in script
    assert "MARKET_GUARD_USE_UAT_RUN_CACHE" in script
    assert "use_run_cache" in script
    assert "run_cache_hit_count" in script
    assert "item_cache_status" in script
    assert "akshare.fund_etf_spot_em" in script
    assert "price_reconciliation_report.md" in script
    assert "outputs_uat_summary.md" in script


def test_uat_profiles_doc_contract():
    doc = (PROJECT_ROOT / "docs" / "uat_profiles.md").read_text(encoding="utf-8")
    cache_doc = (PROJECT_ROOT / "docs" / "uat_run_cache.md").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    for phrase in ["quick", "intraday", "full", "skipped_by_profile", "UseRunCache"]:
        assert phrase in doc
    for phrase in ["opt-in", "akshare", "fund_etf_spot_em", "minute bars", "strict"]:
        assert phrase in cache_doc
    assert "docs/uat_profiles.md" in readme
    assert "docs/uat_run_cache.md" in readme
    assert ".\\scripts\\run_uat.ps1 -Mode full" in readme
    assert ".\\scripts\\run_uat.ps1 -Mode full -UseRunCache" in readme


def _section(report: str, start: str, end: str) -> str:
    return report.split(f"## {start}", 1)[1].split(f"## {end}", 1)[0]
