from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path

import yaml


OUTPUT_DIR = Path("outputs_operation_data_source_feasibility_latest")
FORBIDDEN_ADVICE_PATTERN = re.compile(
    "买入|卖出|加仓|减仓|做T|挂单|目标价|入场价|止损|preferred_action|action_hint|buy|sell|add|reduce",
    re.IGNORECASE,
)


def _ensure_outputs() -> None:
    required = [
        OUTPUT_DIR / "feasibility_matrix.csv",
        OUTPUT_DIR / "feasibility_matrix.json",
        OUTPUT_DIR / "feasibility_summary.md",
        OUTPUT_DIR / "feasibility_summary.json",
    ]
    if all(path.exists() for path in required):
        return
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(Path("scripts/build_operation_data_source_feasibility.ps1")),
        ],
        check=True,
    )


def _symbols(path: str) -> list[str]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return list(data["symbols"])


def _tech_counts() -> dict[str, int]:
    return {
        "operation": len(_symbols("config/universes/tech_core.yaml")),
        "operation_candidate": len(_symbols("config/universes/tech_operation_candidates.yaml")),
        "watchlist": len(_symbols("config/universes/tech_watchlist.yaml")),
        "scan": len(_symbols("config/universes/tech_scan_ai.yaml")),
    }


def _matrix_rows() -> list[dict[str, str]]:
    _ensure_outputs()
    with (OUTPUT_DIR / "feasibility_matrix.csv").open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _row(name: str) -> dict[str, str]:
    rows = {row["provider_name"]: row for row in _matrix_rows()}
    return rows[name]


def test_current_account_baselines_for_v0754():
    assert _tech_counts() == {
        "operation": len(_symbols("config/universes/tech_core.yaml")),
        "operation_candidate": len(_symbols("config/universes/tech_operation_candidates.yaml")),
        "watchlist": len(_symbols("config/universes/tech_watchlist.yaml")),
        "scan": len(_symbols("config/universes/tech_scan_ai.yaml")),
    }

    assert len(_symbols("config/universes/energy_core.yaml")) == 4
    assert len(_symbols("config/universes/energy_operation_candidates.yaml")) == 8
    assert len(_symbols("config/universes/energy_watchlist.yaml")) == 24
    assert len(_symbols("config/universes/energy_scan.yaml")) == 41


def test_feasibility_docs_and_outputs_exist():
    _ensure_outputs()
    for path in [
        "docs/OPERATION_PROVIDER_REQUIREMENTS.md",
        "docs/OPERATION_DATA_SOURCE_FEASIBILITY_MATRIX.md",
        "docs/IQUANT_FEASIBILITY_ASSESSMENT.md",
        "docs/HANDOFF_v0.7.5.4.md",
        OUTPUT_DIR / "feasibility_matrix.csv",
        OUTPUT_DIR / "feasibility_matrix.json",
        OUTPUT_DIR / "feasibility_summary.md",
        OUTPUT_DIR / "feasibility_summary.json",
    ]:
        assert Path(path).exists(), path


def test_current_provider_roles_are_not_operation_primary():
    eastmoney = _row("Eastmoney Direct")
    akshare = _row("AKShare")
    yf = _row("yfinance")
    mock = _row("mock")

    assert "legacy_operation_input" in eastmoney["recommended_role"]
    assert eastmoney["decision"] == "keep_current_not_operation_primary"
    assert "operation_primary" not in eastmoney["recommended_role"]

    assert "legacy_operation_input" in akshare["recommended_role"]
    assert akshare["decision"] == "keep_current_not_operation_primary"
    assert "operation_primary" not in akshare["recommended_role"]

    assert yf["recommended_role"] == "global_reference / US-HK fallback"
    assert yf["decision"] == "keep_current_not_a_share_operation_primary"

    assert mock["recommended_role"] == "development_fallback only"
    assert mock["operation_primary_score"] == "0"


def test_iquant_and_next_targets_are_classified():
    iquant = _row("Guosen iQuant")
    qmt = _row("QMT / miniQMT")
    ptrade = _row("PTrade")

    assert iquant["decision"] == "not_automated_provider"
    assert "manual_verification_source" in iquant["recommended_role"]
    assert "internal_strategy_platform_candidate" in iquant["recommended_role"]

    assert qmt["recommended_role"] == "first-priority feasibility target"
    assert qmt["decision"] == "spike_first"

    assert "feasibility target" in ptrade["recommended_role"]


def test_summary_contract_and_non_changes():
    _ensure_outputs()
    summary = json.loads((OUTPUT_DIR / "feasibility_summary.json").read_text(encoding="utf-8-sig"))
    text = (OUTPUT_DIR / "feasibility_summary.md").read_text(encoding="utf-8-sig")

    assert summary["version"] == "v0.7.5.4"
    assert summary["scope_classification"] == "operation data source feasibility matrix and readiness-tier design"
    assert "No dual-source hard gate is enabled" in summary["no_dual_source_hard_gate_statement"]
    assert "does not change provider_router" in summary["no_pipeline_impact_statement"]
    assert "legacy_operation" in summary["operation_readiness_tiers"]
    assert "Guosen iQuant has strong internal quote capability" in summary["iQuant_conclusion"]
    assert "QMT / miniQMT external Python API feasibility check" in summary["top_next_candidates"][0]
    assert "PTrade external API feasibility check" in summary["top_next_candidates"][1]

    assert "legacy_operation | protected current path" in text
    assert "No dual-source hard gate is enabled" in text


def test_provider_router_strict_and_usable_semantics_are_documented_as_unchanged():
    requirements = Path("docs/OPERATION_PROVIDER_REQUIREMENTS.md").read_text(encoding="utf-8")
    handoff = Path("docs/HANDOFF_v0.7.5.4.md").read_text(encoding="utf-8")

    for expected in [
        "usable_for_operation | unchanged",
        "strict | unchanged",
        "quote_trust_tier | unchanged",
        "provider_router | main routing logic unchanged",
    ]:
        assert expected in requirements
        assert expected in handoff


def test_no_dual_source_hard_gate_is_enabled_in_docs():
    for path in [
        "docs/OPERATION_PROVIDER_REQUIREMENTS.md",
        "docs/OPERATION_DATA_SOURCE_FEASIBILITY_MATRIX.md",
        OUTPUT_DIR / "feasibility_summary.md",
    ]:
        text = Path(path).read_text(encoding="utf-8-sig")
        assert "No dual-source hard gate is enabled" in text or "dual-source hard gate | not enabled" in text


def test_no_trading_advice_keywords_in_v0754_assets():
    _ensure_outputs()
    paths = [
        Path("docs/OPERATION_PROVIDER_REQUIREMENTS.md"),
        Path("docs/OPERATION_DATA_SOURCE_FEASIBILITY_MATRIX.md"),
        Path("docs/IQUANT_FEASIBILITY_ASSESSMENT.md"),
        Path("docs/HANDOFF_v0.7.5.4.md"),
        OUTPUT_DIR / "feasibility_summary.md",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8-sig")
        assert not FORBIDDEN_ADVICE_PATTERN.search(text), path
