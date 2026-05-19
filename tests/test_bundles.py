from __future__ import annotations

from pathlib import Path

import pytest

from market_price_guard.main import PROJECT_ROOT, run_pipeline


@pytest.mark.parametrize(
    ("profile", "provider_policy", "quote_purpose", "expected_block", "forbidden_blocks"),
    [
        ("tech", "fast", "operation", "tech_price_block.md", ["energy_price_block.md", "controller_price_summary.md"]),
        ("tech", "fast", "reference", "tech_price_block.md", ["energy_price_block.md", "controller_price_summary.md"]),
        ("energy", "fast", "operation", "energy_price_block.md", ["tech_price_block.md", "controller_price_summary.md"]),
        ("all", "fast", "operation", "controller_price_summary.md", ["energy_price_block.md", "tech_price_block.md"]),
        ("all", "diagnostic", "operation", None, ["energy_price_block.md", "tech_price_block.md", "controller_price_summary.md"]),
    ],
)
def test_bundle_generation_and_profile_boundaries(tmp_path, profile, provider_policy, quote_purpose, expected_block, forbidden_blocks):
    output_dir = tmp_path / f"{profile}_{provider_policy}_{quote_purpose}"

    run_pipeline(
        output_dir=output_dir,
        provider_mode="mock",
        profile=profile,
        provider_policy=provider_policy,
        quote_purpose=quote_purpose,
        strict=quote_purpose == "operation",
    )

    assert (output_dir / "0_upload_bundle.md").exists()
    assert (output_dir / "debug_bundle.md").exists()
    if expected_block:
        assert (output_dir / expected_block).exists()
    for filename in forbidden_blocks:
        assert not (output_dir / filename).exists()


def test_tech_operation_upload_bundle_contains_core_sections(tmp_path):
    output_dir = tmp_path / "tech_operation"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", strict=True)
    bundle = (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")

    assert "quote_purpose: operation" in bundle
    assert "当前用途级别：" in bundle
    for title in ["纳指 / 海外科技ETF", "AI / 人工智能ETF", "通信 / 科技ETF", "黄金防守仓 / 潜在转科技资金", "非科技宽基单独列示"]:
        assert title in bundle


def test_tech_reference_upload_bundle_is_reference_only(tmp_path):
    output_dir = tmp_path / "tech_reference"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", quote_purpose="reference")
    bundle = (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")

    assert "quote_purpose: reference" in bundle
    assert "当前用途级别：reference-only" in bundle
    assert "可用于快速参考：是" in bundle
    assert "可用于具体操作建议：否" in bundle
    assert "confirmation_required" in bundle
    for title in ["纳指 / 海外科技ETF", "AI / 人工智能ETF", "通信 / 科技ETF"]:
        assert title in bundle


def test_energy_and_controller_upload_bundle_scope(tmp_path):
    energy_dir = tmp_path / "energy"
    all_dir = tmp_path / "all"

    run_pipeline(output_dir=energy_dir, provider_mode="mock", profile="energy", strict=True)
    run_pipeline(output_dir=all_dir, provider_mode="mock", profile="all", strict=True)
    energy_bundle = (energy_dir / "0_upload_bundle.md").read_text(encoding="utf-8")
    all_bundle = (all_dir / "0_upload_bundle.md").read_text(encoding="utf-8")

    for symbol in ["00883.HK", "601899.SH", "601985.SH", "003816.SZ"]:
        assert symbol in energy_bundle
    assert "总控摘要" in all_bundle
    assert "Provider attempts by symbol" not in all_bundle
    assert "### 能源账户核心价格" not in all_bundle
    assert "### 科技账户" not in all_bundle


def test_diagnostic_upload_bundle_is_diagnostic_only(tmp_path):
    output_dir = tmp_path / "diagnostic"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="all", provider_policy="diagnostic")
    bundle = (output_dir / "0_upload_bundle.md").read_text(encoding="utf-8")

    assert "当前用途级别：diagnostic-only" in bundle
    assert "诊断输出用于排查" in bundle


def test_debug_bundle_contains_provider_runtime_and_snapshot(tmp_path):
    output_dir = tmp_path / "debug"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", quote_purpose="reference")
    debug = (output_dir / "debug_bundle.md").read_text(encoding="utf-8")

    for expected in [
        "Provider Health 摘要",
        "Runtime Diagnostics 摘要",
        "prices_snapshot 关键明细摘要",
        "selected_provider",
        "fallback_used",
        "provider_error",
        "quote_trust_tier",
        "confirmation_required",
    ]:
        assert expected in debug


def test_bundles_do_not_contain_actionable_advice_terms(tmp_path):
    output_dir = tmp_path / "bundles"

    run_pipeline(output_dir=output_dir, provider_mode="mock", profile="tech", quote_purpose="reference")
    forbidden = ["建议买入", "建议卖出", "买入", "卖出", "加仓", "减仓", "做T", "目标价", "挂单价"]

    for filename in ["0_upload_bundle.md", "debug_bundle.md"]:
        content = (output_dir / filename).read_text(encoding="utf-8")
        for term in forbidden:
            assert term not in content


def test_contract_docs_and_uat_script_include_bundles():
    output_contract = (PROJECT_ROOT / "docs" / "output_contract.md").read_text(encoding="utf-8")
    uat_checklist = (PROJECT_ROOT / "docs" / "uat_checklist.md").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    run_uat = (PROJECT_ROOT / "scripts" / "run_uat.ps1").read_text(encoding="utf-8")

    for content in [output_contract, uat_checklist, readme, run_uat]:
        assert "0_upload_bundle.md" in content
        assert "debug_bundle.md" in content
    assert "run_tech_fast_reference.ps1" in run_uat
    assert "strict_blocked_but_reported" in run_uat


def test_upload_bundle_filename_sorts_first():
    assert Path("0_upload_bundle.md").name.startswith("0_")
