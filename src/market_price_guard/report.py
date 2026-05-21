from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .models import PriceRecord
from .price_reconciliation import build_reconciliation_report, reconciliation_summary


PROVIDER_CAPABILITIES_PATH = Path("config/provider_capabilities.yaml")


OUTPUT_COLUMNS = [
    "project",
    "symbol",
    "name",
    "market",
    "price",
    "last_price",
    "prev_close",
    "open_price",
    "high_price",
    "low_price",
    "volume",
    "amount",
    "price_change",
    "price_change_pct",
    "amplitude_pct",
    "currency",
    "source",
    "selected_provider",
    "quote_time",
    "fetch_time",
    "market_status",
    "is_stale",
    "stale_reason",
    "usable_for_operation",
    "required_for_operation",
    "quote_trust_tier",
    "usable_for_reference",
    "quote_purpose",
    "confirmation_required",
    "operation_blocking_reason",
    "reference_note",
    "reconciliation_enabled",
    "source_agreement_status",
    "compared_sources",
    "reference_source",
    "candidate_source",
    "price_diff_abs",
    "price_diff_pct",
    "quote_time_gap_seconds",
    "reconciliation_note",
    "operation_candidate_agreed",
    "asset_type",
    "project_scope",
    "role",
    "universe_tags",
    "universe_type",
    "default_quote_purpose",
    "report_group",
    "notes",
    "registry_found",
    "unsupported_reason",
    "affect_core_strict",
    "operation_candidate",
    "candidate_quote_ready",
    "candidate_data_status",
    "candidate_blocking_reason",
    "candidate_next_step",
    "last_price_source",
    "prev_close_source",
    "open_price_source",
    "high_price_source",
    "low_price_source",
    "volume_source",
    "amount_source",
    "price_change_source",
    "price_change_pct_source",
    "amplitude_pct_source",
    "base_quote_completeness",
    "base_quote_fields_available_count",
    "base_quote_fields_missing_count",
    "base_quote_missing_fields",
    "base_quote_field_errors",
    "exchange",
    "country_market",
    "trading_calendar",
    "field_quality_summary",
    "field_validation_status",
    "volume_unit",
    "amount_unit",
    "volume_unit_confidence",
    "amount_unit_confidence",
    "volume_comparable_across_providers",
    "amount_comparable_across_providers",
    "price_change_pct_comparable",
    "base_quote_comparable_score",
    "provider_capability_status",
    "provider_capability_notes",
    "rankable",
    "rank_exclusion_reason",
    "scan_status",
    "watch_priority",
    "scan_score_basic",
    "data_quality_score",
    "momentum_score_basic",
    "field_reliability_score",
    "liquidity_score_basic",
    "reconciliation_score",
    "scan_score_notes",
    "minute_bars_available",
    "minute_bar_provider",
    "minute_bar_interval",
    "minute_bar_count",
    "minute_bar_latest_time",
    "minute_bar_fetch_time",
    "minute_bar_status",
    "minute_bar_validation_status",
    "minute_bar_missing_reason",
    "minute_bar_notes",
    "minute_bar_market_session",
    "minute_bar_after_close_possible",
    "minute_bar_retry_suggested",
    "minute_bar_retry_reason",
    "minute_bar_after_close_applies_to",
    "minute_bar_upload_note",
    "yfinance_ticker",
]

GOLD_NOTE = (
    "黄金持仓参考价为用户手工录入价，不等同于国际现货金价；"
    "用于科技账户防守仓/潜在转科技资金的参考，实际操作前需核对账户内可卖价、手续费、点差和到账规则。"
)

TECH_GROUPS = [
    ("纳指 / 海外科技ETF", "nasdaq_or_overseas_tech_etf"),
    ("AI / 人工智能ETF", "ai_tech_equity"),
    ("通信 / 科技ETF", "communication_tech_equity"),
    ("黄金防守仓 / 潜在转科技资金", "defense_or_potential_tech_funding"),
    ("非科技宽基单独列示", "non_tech_broad_base_etf"),
]

AKSHARE_FUNCTIONS = [
    "stock_zh_a_spot_em",
    "stock_sh_a_spot_em",
    "stock_sz_a_spot_em",
    "stock_hk_spot_em",
    "stock_hk_main_board_spot_em",
    "stock_hsgt_sh_hk_spot_em",
    "fund_etf_spot_em",
]


@dataclass(frozen=True)
class CompletenessSummary:
    usable_for_operation: bool
    reasons: list[str]
    missing_prices: list[PriceRecord]
    stale_prices: list[PriceRecord]
    quote_time_missing: list[PriceRecord]
    strict_blockers: list[dict[str, Any]]
    manual_records: list[PriceRecord]
    akshare_records: list[PriceRecord]
    warnings: list[str]


def get_blocking_records(records: list[PriceRecord]) -> list[dict[str, Any]]:
    blocking_records: list[dict[str, Any]] = []
    for record in records:
        if not record.required_for_operation:
            continue
        blocking_reason = _blocking_reason(record)
        if blocking_reason:
            diagnostics = record.provider_diagnostics
            blocking_records.append(
                {
                    "project": record.project,
                    "symbol": record.symbol,
                    "name": record.name,
                    "source": record.source,
                    "quote_time": record.quote_time.isoformat() if record.quote_time else "",
                    "is_stale": record.is_stale,
                    "stale_reason": record.stale_reason,
                    "blocking_reason": blocking_reason,
                    "function_name": diagnostics.get("function_name", ""),
                    "provider_status": diagnostics.get("provider_status", ""),
                    "exception_type": diagnostics.get("exception_type", ""),
                }
            )
    return blocking_records


def build_completeness_summary(records: list[PriceRecord]) -> CompletenessSummary:
    missing_prices = [record for record in records if record.price is None]
    quote_time_missing = [
        record for record in records if record.quote_time is None or "quote_time_missing" in record.quality_issues
    ]
    stale_prices = [record for record in records if record.is_stale and record.price is not None]
    strict_blockers = get_blocking_records(records)
    manual_records = [record for record in records if record.source == "manual"]
    akshare_records = [record for record in records if record.source == "akshare"]
    warnings = [
        f"{record.project} {record.symbol} {record.name}: {record.stale_reason}"
        for record in records
        if not record.required_for_operation and (record.is_stale or record.price is None or record.quality_issues)
    ]

    reasons: list[str] = []
    if missing_prices:
        reasons.append("存在价格缺失")
    if stale_prices:
        reasons.append("存在 stale 价格")
    if quote_time_missing:
        reasons.append("存在 quote_time_missing，无法证明价格新鲜")

    return CompletenessSummary(
        usable_for_operation=not strict_blockers,
        reasons=reasons,
        missing_prices=missing_prices,
        stale_prices=stale_prices,
        quote_time_missing=quote_time_missing,
        strict_blockers=strict_blockers,
        manual_records=manual_records,
        akshare_records=akshare_records,
        warnings=warnings,
    )


def records_to_dataframe(records: list[PriceRecord]) -> pd.DataFrame:
    return pd.DataFrame([record.output_dict() for record in records], columns=OUTPUT_COLUMNS)


def write_outputs(records: list[PriceRecord], output_dir: Path, provider_mode: str = "mock", runtime: dict[str, Any] | None = None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime = runtime or {}
    emit_files = _files_for_profile(runtime)
    _remove_unscoped_outputs(output_dir, emit_files)
    df = records_to_dataframe(records)
    df.to_csv(output_dir / "prices_snapshot.csv", index=False, encoding="utf-8-sig")
    if runtime.get("include_minute_bars") and runtime.get("minute_bars_snapshot"):
        pd.DataFrame(runtime.get("minute_bars_snapshot", [])).to_csv(
            output_dir / "minute_bars_snapshot.csv",
            index=False,
            encoding="utf-8-sig",
        )
    (output_dir / "data_completeness_report.md").write_text(build_completeness_report(records, runtime=runtime), encoding="utf-8")
    (output_dir / "runtime_diagnostics.md").write_text(build_runtime_diagnostics_report(records, runtime), encoding="utf-8")
    (output_dir / "price_reconciliation_report.md").write_text(build_price_reconciliation_report(records, runtime), encoding="utf-8")
    (output_dir / "provider_capability_report.md").write_text(build_provider_capability_report(records, runtime), encoding="utf-8")
    (output_dir / "provider_health_report.md").write_text(
        build_provider_health_report(records, provider_mode=provider_mode),
        encoding="utf-8",
    )
    if "energy_price_block.md" in emit_files:
        (output_dir / "energy_price_block.md").write_text(build_project_block(records, "energy", "能源账户价格事实块"), encoding="utf-8")
    if "tech_price_block.md" in emit_files:
        (output_dir / "tech_price_block.md").write_text(build_tech_block(records, runtime=runtime), encoding="utf-8")
    if "controller_price_summary.md" in emit_files:
        (output_dir / "controller_price_summary.md").write_text(build_controller_summary(records), encoding="utf-8")
    if "candidate_watchlist_report.md" in emit_files:
        (output_dir / "candidate_watchlist_report.md").write_text(build_candidate_watchlist_report(records, runtime), encoding="utf-8")
    if "scan_universe_report.md" in emit_files:
        (output_dir / "scan_universe_report.md").write_text(build_scan_universe_report(records, runtime), encoding="utf-8")
    if "operation_candidate_report.md" in emit_files:
        (output_dir / "operation_candidate_report.md").write_text(build_operation_candidate_report(records, runtime), encoding="utf-8")
    if runtime.get("unsupported_count"):
        (output_dir / "unsupported_symbols_report.md").write_text(build_unsupported_symbols_report(runtime), encoding="utf-8")
    (output_dir / "index.md").write_text(
        build_index_report(records, output_dir=output_dir, provider_mode=provider_mode, runtime=runtime),
        encoding="utf-8",
    )
    (output_dir / "0_upload_bundle.md").write_text(
        build_upload_bundle(records, output_dir=output_dir, provider_mode=provider_mode, runtime=runtime),
        encoding="utf-8",
    )
    (output_dir / "debug_bundle.md").write_text(
        build_debug_bundle(records, output_dir=output_dir, provider_mode=provider_mode, runtime=runtime),
        encoding="utf-8",
    )


def build_index_report(
    records: list[PriceRecord],
    output_dir: Path,
    provider_mode: str = "mock",
    runtime: dict[str, Any] | None = None,
) -> str:
    runtime = runtime or {}
    summary = build_completeness_summary(records)
    issue_counts = _index_issue_counts(records, summary, runtime)
    quote_purpose = str(runtime.get("quote_purpose", "operation"))
    usable_text = "否" if quote_purpose == "reference" else ("是" if summary.usable_for_operation else "否")
    provider_counts = _selected_provider_counts(records)
    recommended_files = _recommended_files(
        profile=str(runtime.get("profile", "")),
        provider_policy=str(runtime.get("provider_policy", "")),
    )
    lines = [
        "# market_price_guard 本轮刷新索引",
        "",
        "## 基本信息",
        f"- generated_at: {runtime.get('run_end_time_utc', '')}",
        f"- profile: {runtime.get('profile', '')}",
        f"- provider_mode: {runtime.get('provider_mode', provider_mode)}",
        f"- provider_policy: {runtime.get('provider_policy', '')}",
        f"- reconcile_mode: {runtime.get('reconcile_mode', 'default')}",
        f"- strict: {str(runtime.get('strict', False)).lower()}",
        f"- exit_code: {runtime.get('exit_code', '')}",
        f"- output_dir: {output_dir}",
        f"- quote_purpose: {quote_purpose}",
        f"- reconcile_mode: {runtime.get('reconcile_mode', 'default')}",
        f"- universe_name: {runtime.get('universe_name', '')}",
        f"- universe_type: {runtime.get('universe_type', '')}",
        "",
        "## 本轮结论",
        f"- 可用于具体操作建议：{usable_text}",
    ]
    if quote_purpose == "reference":
        lines.extend(
            [
                "- 本轮为快速参考模式。",
                "- 可用于快速参考：是",
                "- 不可用于具体操作建议。",
                "- 如需具体执行动作或盘中价位，必须运行 operation-grade / strict 输出。",
            ]
        )
    if not summary.usable_for_operation:
        lines.extend(
            [
                f"- strict blocking records 数量: {issue_counts['blocking_records']}",
                f"- provider_error 数量: {issue_counts['provider_error']}",
                f"- stale 数量: {issue_counts['stale']}",
                f"- quote_time_missing 数量: {issue_counts['quote_time_missing']}",
                f"- mock fallback not usable 数量: {issue_counts['mock_fallback_not_usable']}",
                f"- run_time_budget_exceeded: {runtime.get('run_time_budget_exceeded', False)}",
            ]
        )
    lines.extend(["", "## Blocking Records 摘要"])
    if summary.strict_blockers:
        lines.extend(_index_blocking_lines(summary.strict_blockers))
    else:
        lines.append("- 无")
    lines.extend(["", "## 核心价格覆盖摘要"])
    lines.extend(_coverage_summary_lines(records, str(runtime.get("profile", ""))))
    lines.extend(["", "## Quote trust summary"])
    lines.extend(_quote_trust_summary_lines(records, quote_purpose))
    lines.extend(["", "## Reconciliation summary"])
    lines.extend(_reconciliation_summary_lines(records))
    lines.extend(
        [
            "",
            "## 运行时效摘要",
            f"- total_elapsed_seconds: {runtime.get('total_elapsed_seconds', '')}",
            f"- max_quote_lag_seconds: {runtime.get('max_quote_lag_seconds', '')}",
            f"- run_time_budget_exceeded: {runtime.get('run_time_budget_exceeded', False)}",
            f"- slow_provider_attempts 数量: {issue_counts['slow_provider_attempts']}",
            f"- provider calls: {_provider_call_total(records)}",
            f"- cache hits: {_provider_cache_hits(records)}",
            f"- oldest_quote_time: {_oldest_quote_time(records)}",
            f"- newest_quote_time: {_newest_quote_time(records)}",
            "",
            "## Provider 摘要",
        ]
    )
    if provider_counts:
        lines.extend([f"- {provider}: {count}" for provider, count in sorted(provider_counts.items())])
    else:
        lines.append("- 无")
    lines.extend(
        [
            f"- fallback_used 数量: {issue_counts['fallback_used']}",
            f"- mock fallback not usable 数量: {issue_counts['mock_fallback_not_usable']}",
            "",
            "## 推荐复制给项目的文件",
        ]
    )
    lines.extend([f"- {filename}" for filename in recommended_files])
    if runtime.get("include_minute_bars") and runtime.get("minute_bars_snapshot"):
        lines.append("- minute_bars_snapshot.csv")
    lines.extend(
        [
            "",
            "## 报告入口",
            "- data_completeness_report.md",
            "- provider_health_report.md",
            "- runtime_diagnostics.md",
            "",
            "本索引只汇总数据状态、可用性、阻断原因和建议查看的报告文件。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_upload_bundle(
    records: list[PriceRecord],
    output_dir: Path,
    provider_mode: str = "mock",
    runtime: dict[str, Any] | None = None,
) -> str:
    runtime = runtime or {}
    profile = str(runtime.get("profile", ""))
    provider_policy = str(runtime.get("provider_policy", ""))
    quote_purpose = str(runtime.get("quote_purpose", "operation"))
    summary = build_completeness_summary(records)
    issue_counts = _index_issue_counts(records, summary, runtime)
    usage_level = _usage_level(records, summary, runtime)
    usable_for_reference = _yes_no(bool(records) and any(record.usable_for_reference for record in records))
    usable_for_operation = _yes_no(usage_level == "operation-ready")
    lines = [
        "# market_price_guard 上传包",
        "",
        "## 基本信息",
        f"- generated_at: {runtime.get('run_end_time_utc', '')}",
        f"- profile: {profile}",
        f"- provider_mode: {runtime.get('provider_mode', provider_mode)}",
        f"- provider_policy: {provider_policy}",
        f"- quote_purpose: {quote_purpose}",
        f"- reconcile_mode: {runtime.get('reconcile_mode', 'default')}",
        f"- strict: {str(runtime.get('strict', False)).lower()}",
        f"- exit_code: {runtime.get('exit_code', '')}",
        f"- output_dir: {output_dir}",
        f"- universe_name: {runtime.get('universe_name', '')}",
        f"- universe_type: {runtime.get('universe_type', '')}",
        f"- core_count: {runtime.get('core_count', '')}",
        f"- watchlist_count: {runtime.get('watchlist_count', '')}",
        f"- scan_count: {runtime.get('scan_count', '')}",
        f"- unsupported_count: {runtime.get('unsupported_count', '')}",
        "",
        "## 本轮结论",
        f"- 可用于快速参考：{usable_for_reference}",
        f"- 可用于具体操作建议：{usable_for_operation}",
        f"- 当前用途级别：{usage_level}",
        f"- confirmation_required 数量: {sum(1 for record in records if record.confirmation_required)}",
        f"- blocking records 数量: {len(summary.strict_blockers)}",
        "",
        "## 数据完整度摘要",
        f"- strict/exit_code: {runtime.get('exit_code', '')}",
        f"- provider_error 数量: {issue_counts['provider_error']}",
        f"- stale 数量: {issue_counts['stale']}",
        f"- quote_time_missing 数量: {issue_counts['quote_time_missing']}",
        f"- invalid_price 数量: {_invalid_price_count(records)}",
        f"- mock fallback not usable 数量: {issue_counts['mock_fallback_not_usable']}",
        f"- run_time_budget_exceeded: {runtime.get('run_time_budget_exceeded', False)}",
        "",
        "### Blocking records 摘要",
    ]
    lines.extend(_blocking_record_lines(summary.strict_blockers))
    lines.extend(["", "## Quote Trust Tier 摘要"])
    lines.extend(_quote_trust_bundle_lines(records))
    base_quote_heading = "## 基础行情摘要 / Base Quote Summary" if profile in {"all", "controller"} else "## 基础行情快照 / Base Quote Snapshot"
    lines.extend(["", base_quote_heading])
    lines.extend(_base_quote_snapshot_lines(records, profile, str(runtime.get("universe_type", ""))))
    lines.extend(["", "## 字段质量提示 / Field Quality Notes"])
    lines.extend(_field_quality_note_lines())
    if _minute_probe_visible(records, runtime):
        lines.extend(["", "## 分钟线探测摘要 / Minute Bars Probe Summary"])
        lines.append("Minute note is compact. Full provider failure details are in debug_bundle.md.")
        lines.extend(_minute_bars_summary_table(records))
        lines.extend(_minute_bars_probe_note_lines())
    if str(runtime.get("universe_type", "")) == "operation_candidate":
        lines.extend(["", "## Operation Candidate Summary"])
        lines.extend(_operation_candidate_summary_lines(records, runtime))
    if str(runtime.get("universe_type", "")) in {"candidate_watchlist", "scan_universe"}:
        lines.extend(["", "## 扫描优先级摘要 / Scan Priority Summary"])
        lines.extend(_scan_priority_summary_table(records))
        lines.extend(["", "## Top Scan Candidates"])
        lines.extend(_top_scan_candidates_table(records, limit=5))
        lines.extend(_scan_ranking_safety_lines())
    lines.extend(["", "## Reconciliation Summary"])
    lines.extend(_reconciliation_summary_lines(records))
    lines.extend(["", "## 项目核心内容"])
    lines.extend(_bundle_project_lines(records, profile, provider_policy, str(runtime.get("universe_type", ""))))
    lines.extend(["", "## Universe isolation"])
    lines.extend(_universe_isolation_lines(runtime))
    lines.extend(["", "## Reference / Operation 使用提示"])
    lines.extend(_bundle_usage_note_lines(quote_purpose, usage_level))
    lines.extend(["", "## Debug 提示"])
    lines.extend(
        [
            "- 如出现 strict=2、blocking records、provider_error、quote_time_missing、invalid_price、stale、selected_provider=mock、fallback_used 异常、run_time_budget_exceeded、slow_provider_attempts、quote_time 可疑或报告冲突，请补充 debug_bundle.md。",
            "- 本上传包只汇总数据状态、可用性和阻断原因。",
        ]
    )
    return _sanitize_bundle_text("\n".join(lines) + "\n")


def build_debug_bundle(
    records: list[PriceRecord],
    output_dir: Path,
    provider_mode: str = "mock",
    runtime: dict[str, Any] | None = None,
) -> str:
    runtime = runtime or {}
    summary = build_completeness_summary(records)
    lines = [
        "# market_price_guard 排障包",
        "",
        "## 基本信息",
        f"- generated_at: {runtime.get('run_end_time_utc', '')}",
        f"- profile: {runtime.get('profile', '')}",
        f"- provider_mode: {runtime.get('provider_mode', provider_mode)}",
        f"- provider_policy: {runtime.get('provider_policy', '')}",
        f"- quote_purpose: {runtime.get('quote_purpose', 'operation')}",
        f"- reconcile_mode: {runtime.get('reconcile_mode', 'default')}",
        f"- strict: {str(runtime.get('strict', False)).lower()}",
        f"- exit_code: {runtime.get('exit_code', '')}",
        f"- output_dir: {output_dir}",
        f"- universe_name: {runtime.get('universe_name', '')}",
        f"- universe_type: {runtime.get('universe_type', '')}",
        "",
        "## Symbol Registry Resolution 摘要",
    ]
    lines.extend(_registry_resolution_lines(runtime))
    lines.extend([
        "",
        "## Provider Health 摘要",
        f"- provider_policy: {_provider_policy_from_records(records)}",
        f"- provider_mode: {provider_mode}",
    ])
    lines.extend(_provider_call_summary_lines(records))
    lines.extend(["", "### Provider attempts"])
    lines.extend(_provider_attempts_by_symbol(records))
    lines.extend(["", "## Runtime Diagnostics 摘要"])
    lines.extend(build_runtime_diagnostics_report(records, runtime).splitlines()[2:])
    lines.extend(["", "## Price Reconciliation 摘要"])
    lines.extend(_reconciliation_detail_lines(records))
    lines.extend(["", "## Base Quote Fields Summary"])
    lines.extend(_base_quote_detail_table(records))
    lines.extend(["", "## Base Quote Field Sources"])
    lines.extend(_base_quote_field_sources_table(records))
    lines.extend(["", "## Provider Capability Summary"])
    lines.append("- full report: provider_capability_report.md")
    lines.extend(_provider_capability_summary_table())
    lines.extend(_field_quality_risk_lines(records))
    lines.extend(["", "## Provider Capability Notes"])
    lines.extend(_provider_capability_note_lines())
    if _minute_probe_visible(records, runtime):
        lines.extend(["", "## Minute Bars Probe Detail"])
        lines.extend(_minute_bars_detail_table(records))
    lines.extend(["", "## Scan Ranking Trace"])
    lines.extend(_scan_ranking_trace_table(records))
    lines.extend(["", "## prices_snapshot 关键明细摘要"])
    lines.extend(_debug_snapshot_table(records))
    lines.extend(["", "## Blocking / Error 摘要"])
    lines.extend(["### Blocking records"])
    lines.extend(_blocking_record_lines(summary.strict_blockers))
    lines.extend(["", "### provider_error"])
    lines.extend(_record_lines([record for record in records if "provider_error" in record.quality_issues], marker="provider_error"))
    lines.extend(["", "### quote_time_missing"])
    lines.extend(_record_lines(summary.quote_time_missing, marker="quote_time_missing"))
    lines.extend(["", "### invalid_price"])
    lines.extend(_record_lines([record for record in records if "invalid_price" in record.quality_issues], marker="invalid_price"))
    lines.extend(["", "### stale"])
    lines.extend(_record_lines(summary.stale_prices))
    lines.extend(["", "### mock fallback not usable"])
    lines.extend(_record_lines([record for record in records if "mock_fallback_not_allowed" in record.quality_issues], marker="mock_fallback_not_allowed"))
    lines.extend(["", "### reference-only but operation requested"])
    lines.extend(_record_lines([record for record in records if record.operation_blocking_reason == "reference_tier_requires_operation_confirmation"], marker="reference_only"))
    lines.extend(["", "本排障包只用于定位 provider、runtime、freshness 和 blocking 问题。"])
    return _sanitize_bundle_text("\n".join(lines) + "\n")


def build_completeness_report(records: list[PriceRecord], runtime: dict[str, Any] | None = None) -> str:
    summary = build_completeness_summary(records)
    runtime = runtime or {}
    quote_purpose = str(runtime.get("quote_purpose", "operation"))
    usable_text = "否" if quote_purpose == "reference" else ("是" if summary.usable_for_operation else "否")
    lines = [
        "# 数据完整度报告",
        "",
        f"quote_purpose: {quote_purpose}",
        f"reconcile_mode: {runtime.get('reconcile_mode', 'default')}",
        f"可用于具体操作建议：{usable_text}",
        "",
        "本工具不做自动交易，不输出买卖建议，只输出价格事实、数据源、时间戳、市场状态和数据完整度。",
        "",
        "行情源健康状态详见 provider_health_report.md。",
        "",
        "## Strict blocking records",
    ]
    if any(record.source == "eastmoney_direct" or record.selected_provider == "eastmoney_direct" for record in records):
        lines.insert(
            7,
            "Eastmoney Direct source limitation: Eastmoney public web quote endpoint; reference / operation-candidate only in this version; not operation-grade by itself.",
        )
    if quote_purpose == "reference":
        lines.extend(
            [
                "",
                "## Reference mode warning",
                "- 本轮为 reference 模式，可用于快速参考，不可用于具体操作建议。",
                "- operation confirmation required: 如需具体执行动作或盘中价位，必须运行 operation-grade / strict 输出。",
            ]
        )
    lines.extend(_blocking_record_lines(summary.strict_blockers))
    lines.extend(["", "## Provider diagnostics"])
    lines.extend(_provider_diagnostics_lines(summary.akshare_records))
    lines.extend(["", "## Provider routing notes"])
    lines.extend(_provider_routing_note_lines(records))
    lines.extend(["", "## Quote trust tier diagnostics"])
    lines.extend(_quote_trust_diagnostic_lines(records))
    lines.extend(["", "## Source agreement diagnostics"])
    lines.extend(_reconciliation_detail_lines(records))
    lines.extend(["", "## Base quote completeness summary"])
    lines.extend(_base_quote_completeness_lines(records))
    lines.extend(_base_quote_caveat_lines())
    lines.extend(["", "## Field Quality / Provider Capability"])
    lines.extend(_field_quality_capability_lines(records))
    lines.extend(["", "## Minute Bars Completeness"])
    lines.extend(_minute_bars_completeness_lines(records, runtime))
    lines.extend(["", "## Scan Ranking Summary"])
    lines.extend(_scan_ranking_summary_lines(records))
    lines.append("- See price_reconciliation_report.md for full multi-source comparison details.")
    lines.extend(["", "## Runtime freshness diagnostics"])
    lines.extend(_runtime_freshness_lines(runtime))
    lines.extend(["", "## AKShare price records"])
    lines.extend(_record_lines(summary.akshare_records))
    lines.extend(["", "## AKShare quote freshness details"])
    lines.extend(_akshare_freshness_lines(summary.akshare_records))
    lines.extend(["", "## AKShare / 数据质量问题"])
    lines.extend(_quality_issue_lines(summary.akshare_records))
    lines.extend(["", "## 黄金手工价说明", GOLD_NOTE, "", "## 如果为否，原因"])
    lines.extend(_bullet_lines(summary.reasons))
    lines.extend(["", "## 缺失价格列表"])
    lines.extend(_record_lines(summary.missing_prices))
    lines.extend(["", "## stale 价格列表"])
    lines.extend(_record_lines(summary.stale_prices))
    lines.extend(["", "## quote_time 缺失列表"])
    lines.extend(_record_lines(summary.quote_time_missing, marker="quote_time_missing"))
    lines.extend(["", "## manual price records"])
    lines.extend(_manual_record_lines(summary.manual_records))
    lines.extend(["", "## warning"])
    lines.extend(_bullet_lines(summary.warnings))
    lines.extend(
        [
            "",
            "## 不确定性",
            "- 手续费、点差、赎回到账规则未自动计算。",
            "- GOLD_CNY 需以后续实际账户可卖价为准。",
            "",
            "## 允许使用范围",
            "- 可用于价格事实同步、数据源核对、时间戳核对、市场状态核对和数据完整度检查。",
            "- 收盘后价格仅可作为收盘/最后成交参考。",
            "- GOLD_CNY 仅可作为科技账户防守仓/潜在转科技资金参考。",
            "",
            "## 禁止使用范围",
            "- 不可用于自动交易。",
            "- 不输出买卖建议。",
            "- 若 required_for_operation 指标缺失、stale、quote_time 缺失或无效，不可用于具体操作建议。",
            "- 收盘/最后成交参考价不可用于盘中做T。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_provider_health_report(records: list[PriceRecord], provider_mode: str = "mock") -> str:
    provider_policy = _provider_policy_from_records(records)
    quote_purpose = _quote_purpose_from_records(records)
    lines = [
        "# Provider Health Report",
        "",
        "行情源健康报告仅用于解释价格事实、接口状态和数据完整度，不提供买卖建议，不做自动交易。",
        "",
        f"- provider_policy={provider_policy}",
        f"- quote_purpose={quote_purpose}",
    ]
    if provider_policy == "diagnostic":
        lines.append("- diagnostic mode active: provider diagnostics may run slower than fast mode.")
    lines.extend(["", "## AKShare ETF"])
    lines.extend(_akshare_health_group(records, "ETF", ["fund_etf_spot_em"]))
    lines.extend(["", "## AKShare Minute Bars"])
    lines.extend(_akshare_minute_health_group(records))
    lines.extend(["", "## AKShare A股"])
    lines.extend(_akshare_health_group(records, "A_SHARE", ["stock_zh_a_spot_em", "stock_sh_a_spot_em", "stock_sz_a_spot_em"]))
    lines.extend(["", "## AKShare 港股"])
    lines.extend(
        _akshare_health_group(
            records,
            "HK",
            ["stock_hk_spot_em", "stock_hk_main_board_spot_em", "stock_hsgt_sh_hk_spot_em"],
        )
    )
    lines.extend(["", "## YFinance 港股 / A股"])
    lines.extend(_yfinance_health_group(records))
    lines.extend(["", "## Eastmoney Direct"])
    lines.extend(_eastmoney_direct_health_group(records))
    lines.extend(["", "## Manual"])
    lines.extend(_manual_health_group(records))
    if provider_mode == "mock":
        lines.extend(["", "## Mock"])
        lines.extend(_mock_health_group(records))
    lines.extend(["", "## Provider call summary"])
    lines.extend(_provider_call_summary_lines(records))
    lines.extend(["", "## Provider attempts by symbol"])
    lines.extend(_provider_attempts_by_symbol(records))
    return "\n".join(lines) + "\n"


def build_price_reconciliation_report(records: list[PriceRecord], runtime: dict[str, Any] | None = None) -> str:
    return build_reconciliation_report(records, runtime)


def build_provider_capability_report(records: list[PriceRecord], runtime: dict[str, Any] | None = None) -> str:
    runtime = runtime or {}
    lines = [
        "# Provider Capability Report",
        "",
        "Provider capability data is diagnostic only. It does not upgrade trust tier, change strict, or provide trading advice.",
        "",
        "## Runtime Context",
        f"- generated_at: {runtime.get('run_end_time_utc', '')}",
        f"- profile: {runtime.get('profile', '')}",
        f"- provider_mode: {runtime.get('provider_mode', '')}",
        f"- provider_policy: {runtime.get('provider_policy', '')}",
        f"- quote_purpose: {runtime.get('quote_purpose', 'operation')}",
        f"- universe_name: {runtime.get('universe_name', '')}",
        f"- universe_type: {runtime.get('universe_type', '')}",
        "",
        "## Provider Capability Summary",
    ]
    lines.extend(_provider_capability_summary_table())
    lines.extend(["", "## Field Capability Matrix By Provider"])
    lines.extend(_field_capability_matrix_by_provider())
    lines.extend(["", "## Symbol Field Quality"])
    lines.extend(_symbol_field_quality_table(records))
    lines.extend(["", "## Minute Bars Capability"])
    lines.extend(_minute_bars_capability_lines(records, runtime))
    lines.extend(["", "## Safe Usage Notes"])
    lines.extend(_provider_capability_safe_usage_lines())
    return "\n".join(lines) + "\n"


def build_runtime_diagnostics_report(records: list[PriceRecord], runtime: dict[str, Any]) -> str:
    attempts = _all_provider_attempts(records)
    per_provider = _per_provider_elapsed(attempts)
    slow_attempts = [attempt for attempt in attempts if attempt.get("slow_provider_attempt")]
    quote_times = [record.quote_time for record in records if record.quote_time is not None]
    lines = [
        "# Runtime Diagnostics",
        "",
        f"- run_start_time_utc: {runtime.get('run_start_time_utc', '')}",
        f"- run_end_time_utc: {runtime.get('run_end_time_utc', '')}",
        f"- total_elapsed_seconds: {runtime.get('total_elapsed_seconds', '')}",
        f"- profile: {runtime.get('profile', '')}",
        f"- provider_mode: {runtime.get('provider_mode', '')}",
        f"- provider_policy: {runtime.get('provider_policy', '')}",
        f"- strict: {runtime.get('strict', '')}",
        f"- quote_purpose: {runtime.get('quote_purpose', 'operation')}",
        f"- reconcile_mode: {runtime.get('reconcile_mode', 'default')}",
        f"- include_minute_bars: {runtime.get('include_minute_bars', False)}",
        f"- universe_name: {runtime.get('universe_name', '')}",
        f"- universe_type: {runtime.get('universe_type', '')}",
        f"- run_time_budget_exceeded: {runtime.get('run_time_budget_exceeded', False)}",
        f"- max_run_seconds: {runtime.get('max_run_seconds', '')}",
        f"- max_data_lag_seconds: {runtime.get('max_data_lag_seconds', '')}",
        f"- max_quote_lag_seconds: {runtime.get('max_quote_lag_seconds', '')}",
        f"- oldest_quote_time: {min(quote_times).isoformat() if quote_times else ''}",
        f"- newest_quote_time: {max(quote_times).isoformat() if quote_times else ''}",
        "",
        "## per_provider_elapsed_seconds",
    ]
    if per_provider:
        lines.extend([f"- {provider}: {elapsed}" for provider, elapsed in per_provider.items()])
    else:
        lines.append("- 无")
    lines.extend(["", "## per_symbol_elapsed_seconds"])
    symbol_elapsed = _per_symbol_elapsed(records)
    if symbol_elapsed:
        lines.extend([f"- {symbol}: {elapsed}" for symbol, elapsed in symbol_elapsed.items()])
    else:
        lines.append("- 无")
    lines.extend(["", "## slow_provider_attempts"])
    if slow_attempts:
        for attempt in slow_attempts:
            lines.append(
                "- symbol={symbol}, provider={provider}, function_name={function_name}, elapsed_seconds={elapsed_seconds}, timeout_seconds={timeout_seconds}, reason={reason}".format(
                    symbol=attempt.get("symbol", ""),
                    provider=attempt.get("provider", ""),
                    function_name=attempt.get("function_name", ""),
                    elapsed_seconds=attempt.get("elapsed_seconds", ""),
                    timeout_seconds=attempt.get("timeout_seconds", ""),
                    reason=attempt.get("reason", "slow_provider_attempt"),
                )
            )
    else:
        lines.append("- 无")
    lines.extend(["", "## provider_call_cache"])
    lines.extend(_runtime_provider_cache_lines(records))
    if runtime.get("provider_policy") == "diagnostic":
        lines.extend(["", "## provider_policy_note", "- diagnostic mode active: may run slower than fast mode."])
    return "\n".join(lines) + "\n"


def build_project_block(records: list[PriceRecord], project: str, title: str) -> str:
    project_records = [record for record in records if record.project == project]
    lines = [f"# {title}", "", "仅为价格事实和新鲜度记录，不包含买卖建议。", ""]
    lines.extend(_price_table(project_records))
    lines.extend(["", "## 基础行情字段 / Base Quote Fields"])
    lines.extend(_base_quote_fields_table(project_records))
    lines.extend(_base_quote_unit_note_lines())
    return "\n".join(lines) + "\n"


def build_tech_block(records: list[PriceRecord], runtime: dict[str, Any] | None = None) -> str:
    runtime = runtime or {}
    project_records = [record for record in records if record.project == "tech"]
    lines = ["# 科技账户价格事实块", "", "仅为价格事实和新鲜度记录，不包含买卖建议。"]
    if runtime.get("quote_purpose") == "reference" and runtime.get("reconcile_mode") == "full":
        lines.extend(
            [
                "",
                "## Reference / Reconcile Boundary",
                "- quote_purpose=reference",
                "- reconcile_mode=full",
                "- This block is for multi-source reconciliation review only.",
                "- It is not operation-grade and must not be used for concrete operation advice.",
                "- It does not upgrade any quote to operation.",
            ]
        )
    for title, asset_role in TECH_GROUPS:
        grouped = [record for record in project_records if record.asset_role == asset_role]
        lines.extend(["", f"## {title}"])
        if asset_role == "defense_or_potential_tech_funding":
            lines.append(GOLD_NOTE)
        lines.extend(_price_table(grouped))
    lines.extend(["", "## 基础行情字段 / Base Quote Fields"])
    lines.extend(_base_quote_fields_table(project_records))
    lines.extend(_base_quote_unit_note_lines())
    return "\n".join(lines) + "\n"


def build_candidate_watchlist_report(records: list[PriceRecord], runtime: dict[str, Any]) -> str:
    candidates = [record for record in records if record.universe_type == "candidate_watchlist"]
    lines = [
        "# Candidate Watchlist Report",
        "",
        "Candidate watchlist records are reference/conditional observations. They do not affect core operation strict.",
        "",
        f"- universe_name: {runtime.get('universe_name', '')}",
        f"- universe_type: {runtime.get('universe_type', 'candidate_watchlist')}",
        "",
    ]
    lines.extend(_watchlist_table(candidates or records))
    lines.extend(["", "## Watchlist Review Priority"])
    lines.extend(_watchlist_review_priority_table(candidates or records))
    lines.extend(["", "## Compact Base Quote Table"])
    lines.extend(_watchlist_base_quote_table(candidates or records, scan=False))
    lines.extend(["", "## Base Quote Summary"])
    lines.extend(_base_quote_completeness_lines(candidates or records))
    lines.extend(["", "## Provider Coverage / Failure Reasons"])
    lines.extend(_watchlist_scan_failure_reason_table(candidates or records))
    lines.extend(["", "## Safety Notes"])
    lines.extend(_scan_ranking_safety_lines())
    return "\n".join(lines) + "\n"


def build_scan_universe_report(records: list[PriceRecord], runtime: dict[str, Any]) -> str:
    scan_records = [record for record in records if record.universe_type == "scan_universe"]
    lines = [
        "# Scan Universe Report",
        "",
        "Scan universe records are for opportunity observation and data completeness checks only. They do not affect core operation strict.",
        "",
        f"- universe_name: {runtime.get('universe_name', '')}",
        f"- universe_type: {runtime.get('universe_type', 'scan_universe')}",
        "- data_status: price_change_pct/amount/volume may be missing in this version.",
        "",
    ]
    lines.extend(_watchlist_table(scan_records or records))
    lines.extend(["", "# Scan Universe Basic Ranking"])
    lines.extend(
        [
            "- This is a review-priority ranking, not trading advice.",
            "- It does not produce execution instructions.",
            "- Operation decisions require operation-grade price guard output.",
            "- volume/amount are not used for cross-provider liquidity ranking unless comparable flags allow it.",
        ]
    )
    lines.extend(["", "## Scan Summary"])
    lines.extend(_scan_ranking_summary_lines(scan_records or records))
    lines.extend(["", "## Basic Ranking Table"])
    lines.extend(_scan_basic_ranking_table(scan_records or records))
    lines.extend(["", "## Not Rankable"])
    lines.extend(_not_rankable_table(scan_records or records))
    lines.extend(["", "## Compact Base Quote Table"])
    lines.extend(_watchlist_base_quote_table(scan_records or records, scan=True))
    lines.extend(["", "## Base Quote Summary"])
    lines.extend(_base_quote_completeness_lines(scan_records or records))
    lines.extend(["", "## Provider Coverage / Failure Reasons"])
    lines.extend(_watchlist_scan_failure_reason_table(scan_records or records))
    lines.extend(["", "## Safety Notes"])
    lines.extend(_scan_ranking_safety_lines())
    return "\n".join(lines) + "\n"


def build_operation_candidate_report(records: list[PriceRecord], runtime: dict[str, Any]) -> str:
    candidates = [record for record in records if record.universe_type == "operation_candidate"]
    scoped = candidates or records
    lines = [
        "# Tech Operation Candidate Report",
        "",
        "These are pre-trade verification candidates, not core holdings and not operation-grade.",
        "They do not affect tech_fast_strict or outputs_tech_latest.",
        "This output is not trading advice.",
        "",
        f"- universe_name: {runtime.get('universe_name', 'tech_operation_candidates')}",
        f"- universe_type: {runtime.get('universe_type', 'operation_candidate')}",
        "- quote_purpose: reference",
        "- required_for_operation: false",
        "- usable_for_operation: false",
        "- affect_core_strict: false",
        "- not usable for concrete operation recommendations",
        "",
        "## Operation Candidate Summary",
    ]
    lines.extend(_operation_candidate_summary_lines(scoped, runtime))
    lines.extend(["", "## Candidate Data Status"])
    lines.extend(_operation_candidate_table(scoped))
    lines.extend(["", "## Safety Notes"])
    lines.extend(
        [
            "- Operation candidates are reference-only pre-check records.",
            "- A candidate must be explicitly promoted to core holdings before it can be part of the tech fast strict path.",
            "- Candidate provider failures do not block core operation.",
            "- No trading advice is generated.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_unsupported_symbols_report(runtime: dict[str, Any]) -> str:
    unsupported = runtime.get("unsupported_symbols", []) or []
    lines = [
        "# Unsupported Symbols Report",
        "",
        "Unsupported or unregistered symbols are not operation-grade and do not affect core operation strict.",
        "",
        "| symbol | inferred_market | registry_found | asset_type | universe_type | reason | provider_attempted | provider_status | suggested_fix |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in unsupported:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| {symbol} | {market} | {found} | {asset_type} | {universe_type} | {reason} | {provider} | {status} | {fix} |".format(
                symbol=item.get("symbol", ""),
                market=item.get("inferred_market", ""),
                found=item.get("registry_found", ""),
                asset_type=item.get("asset_type", ""),
                universe_type=item.get("universe_type", ""),
                reason=item.get("reason", ""),
                provider=item.get("provider_attempted", ""),
                status=item.get("provider_status", ""),
                fix=item.get("suggested_fix", ""),
            )
        )
    if not unsupported:
        lines.append("|  |  |  |  |  | none |  |  |  |")
    return "\n".join(lines) + "\n"


def build_controller_summary(records: list[PriceRecord]) -> str:
    energy_records = [record for record in records if record.project == "energy"]
    tech_records = [record for record in records if record.project == "tech"]
    gold = next((record for record in records if record.symbol == "GOLD_CNY"), None)
    broad = next((record for record in records if record.symbol == "510300.SH"), None)
    energy_ok = _required_records_ok(energy_records)
    tech_ok = _required_records_ok(tech_records)
    gold_ok = _record_ok(gold)
    broad_ok = _record_ok(broad)
    operation_grade_complete = all(record.quote_trust_tier == "operation" for record in records if record.required_for_operation)
    reference_count = sum(1 for record in records if record.quote_trust_tier == "reference")
    confirmation_count = sum(1 for record in records if record.confirmation_required)
    allocation_allowed = "是" if energy_ok and tech_ok and gold_ok else "否"
    concrete_forbidden = "否" if allocation_allowed == "是" else "是"

    lines = [
        "# 总控价格摘要",
        "",
        "总控项目只维护摘要同步块，不输出能源/科技账户完整明细。",
        "",
        "| item | value |",
        "|---|---|",
        f"| 能源账户核心价格是否完整 | {_yes_no(energy_ok)} |",
        f"| 科技账户核心价格是否完整 | {_yes_no(tech_ok)} |",
        f"| 黄金参考价是否可用 | {_yes_no(gold_ok)} |",
        f"| 非科技宽基价格是否可用 | {_yes_no(broad_ok)} |",
        f"| 是否允许做资产配置判断 | {allocation_allowed} |",
        f"| 是否禁止具体操作判断 | {concrete_forbidden} |",
        f"| operation-grade 覆盖是否完整 | {_yes_no(operation_grade_complete)} |",
        f"| reference-grade records 数量 | {reference_count} |",
        f"| confirmation_required 是否存在 | {_yes_no(confirmation_count > 0)} |",
        "",
        "说明：若 required_for_operation 指标缺失或过期，相关项目不可用于具体操作建议。",
    ]
    return "\n".join(lines) + "\n"


def format_blocking_record(record: dict[str, Any]) -> str:
    return (
        "- project={project}, symbol={symbol}, name={name}, source={source}, quote_time={quote_time}, "
        "is_stale={is_stale}, stale_reason={stale_reason}, blocking_reason={blocking_reason}, "
        "function_name={function_name}, provider_status={provider_status}, exception_type={exception_type}"
    ).format(**record)


def _blocking_reason(record: PriceRecord) -> str:
    issues = set(record.quality_issues)
    if "provider_error" in issues or "akshare_not_installed" in issues:
        return "provider_error"
    if "provider_timeout" in issues:
        return "provider_timeout"
    if "symbol_not_found" in issues:
        return "symbol_not_found"
    if record.price is None or "invalid_price" in issues:
        return "invalid_price_or_missing_price"
    if "invalid_quote_time" in issues:
        return "invalid_quote_time"
    if record.quote_time is None or "quote_time_missing" in issues:
        return "quote_time_missing"
    if "mock_fallback_not_allowed" in issues:
        return "mock_fallback_not_allowed"
    if "manual_fallback_not_allowed" in issues:
        return "manual_fallback_not_allowed"
    if record.operation_blocking_reason == "reference_tier_requires_operation_confirmation":
        return "reference_tier_requires_operation_confirmation"
    if record.is_stale:
        return "stale"
    return ""


def _required_records_ok(records: list[PriceRecord]) -> bool:
    required = [record for record in records if record.required_for_operation]
    return bool(required) and all(_record_ok(record) for record in required)


def _record_ok(record: PriceRecord | None) -> bool:
    return bool(record and record.price is not None and not record.is_stale and record.quote_time is not None and not _blocking_reason(record))


def _yes_no(value: bool) -> str:
    return "是" if value else "否"


def _blocking_record_lines(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return ["- 无"]
    return [format_blocking_record(record) for record in records]


def _provider_diagnostics_lines(records: list[PriceRecord]) -> list[str]:
    if not records:
        return ["- 无 AKShare 记录"]
    grouped = _group_provider_diagnostics(records)
    statuses = {name: grouped.get(name, {}).get("status", "not_called") for name in AKSHARE_FUNCTIONS}
    lines = []
    if any(status == "success" for status in statuses.values()) and any(status == "fail" for status in statuses.values()):
        lines.append("- AKShare partially succeeded")
    if all(status == "fail" for status in statuses.values()):
        lines.append("- AKShare 全部接口调用失败")
    for function_name in AKSHARE_FUNCTIONS:
        diagnostic = grouped.get(function_name)
        if not diagnostic:
            lines.append(f"- {function_name}: not_called")
            continue
        status = diagnostic.get("status", "unknown")
        provider_status = diagnostic.get("provider_status", "")
        line = f"- {function_name}: {status}"
        if provider_status:
            line += f", provider_status={provider_status}"
        if status == "success":
            line += f", returned_rows={diagnostic.get('returned_rows', '')}, matched_symbols={diagnostic.get('matched_symbols', [])}"
        else:
            line += (
                f", exception_type={diagnostic.get('exception_type', '')}, "
                f"exception_message={diagnostic.get('exception_message', '')}"
            )
        lines.append(line)
    return lines


def _akshare_health_group(records: list[PriceRecord], category: str, function_names: list[str]) -> list[str]:
    category_records = [
        record
        for record in records
        if (
            record.source == "akshare" and record.provider_diagnostics.get("category") == category
        )
        or _record_has_attempt_function(record, function_names)
    ]
    grouped = _group_provider_diagnostics(category_records)
    lines = [
        "- provider: akshare",
        f"- market_category: {category}",
        f"- affected_symbols: {_symbols(category_records)}",
        f"- quote_time_status: {_quote_time_status(category_records)}",
        f"- usable_for_operation: {_usable_for_operation(category_records)}",
    ]
    if not category_records:
        lines.append("- status: not_called")
    for function_name in function_names:
        diagnostic = grouped.get(function_name)
        if not diagnostic:
            lines.append(f"- function_name={function_name}, status=not_called")
            continue
        status = _provider_health_status(diagnostic)
        lines.append(
            "- function_name={function_name}, status={status}, returned_rows={returned_rows}, matched_symbols={matched_symbols}, affected_symbols={affected_symbols}, exception_type={exception_type}, exception_message={exception_message}".format(
                function_name=function_name,
                status=status,
                returned_rows=diagnostic.get("returned_rows", ""),
                matched_symbols=_format_symbols(diagnostic.get("matched_symbols", [])),
                affected_symbols=_symbols(category_records),
                exception_type=diagnostic.get("exception_type", ""),
                exception_message=diagnostic.get("exception_message", ""),
            )
        )
    return lines


def _akshare_minute_health_group(records: list[PriceRecord]) -> list[str]:
    minute_records = [
        record
        for record in records
        if "akshare" in _minute_bar_attempted_set(record) or record.minute_bar_provider == "akshare"
    ]
    lines = [
        "- provider: akshare",
        "- function_name=fund_etf_hist_min_em",
        f"- affected_symbols: {_symbols(minute_records)}",
    ]
    if not minute_records:
        lines.append("- status: not_called")
        return lines
    status_counts: dict[str, int] = {}
    for record in minute_records:
        status = _akshare_minute_status(record)
        status_counts[status] = status_counts.get(status, 0) + 1
    lines.append(
        "- status_counts: " + ", ".join(f"{status}:{count}" for status, count in sorted(status_counts.items()))
    )
    for record in minute_records:
        lines.append(
            "- symbol={symbol}, status={status}, reason={reason}, market_session={session}, after_close_possible={after_close}, retry_suggested={retry}".format(
                symbol=record.symbol,
                status=_akshare_minute_status(record),
                reason=_akshare_minute_reason(record),
                session=record.minute_bar_market_session,
                after_close=record.minute_bar_after_close_possible,
                retry=record.minute_bar_retry_suggested,
            )
        )
    return lines


def _manual_health_group(records: list[PriceRecord]) -> list[str]:
    manual_records = [record for record in records if record.source == "manual"]
    if not manual_records:
        return ["- provider: manual", "- status: not_called"]
    lines = [
        "- provider: manual",
        f"- affected_symbols: {_symbols(manual_records)}",
        f"- quote_time_status: {_quote_time_status(manual_records)}",
        f"- usable_for_operation: {_usable_for_operation(manual_records)}",
    ]
    for record in manual_records:
        status = "success"
        if record.quality_issues:
            status = "invalid"
        elif record.is_stale:
            status = "stale"
        lines.append(
            "- symbol={symbol}, status={status}, quote_time={quote_time}, source_note={source_note}".format(
                symbol=record.symbol,
                status=status,
                quote_time=record.quote_time.isoformat() if record.quote_time else "",
                source_note=record.source_note or "",
            )
        )
    return lines


def _yfinance_health_group(records: list[PriceRecord]) -> list[str]:
    yfinance_records = [
        record
        for record in records
        if record.source == "yfinance" or record.selected_provider == "yfinance" or "yfinance" in _minute_bar_attempted_set(record)
    ]
    if not yfinance_records:
        return ["- provider: yfinance", "- market_category: HK/A_SHARE", "- status: not_called"]
    lines = [
        "- provider: yfinance",
        "- market_category: HK/A_SHARE",
        f"- affected_symbols: {_symbols(yfinance_records)}",
        f"- quote_time_status: {_quote_time_status(yfinance_records)}",
        f"- usable_for_operation: {_usable_for_operation(yfinance_records)}",
        "- source_limit_note: yfinance is an open-source Yahoo Finance public API wrapper for research/educational use; not an official exchange feed",
    ]
    for record in yfinance_records:
        diagnostic = _record_provider_attempt(record, "yfinance.Ticker") or record.provider_diagnostics
        lines.append(
            "- function_name={function_name}, status={status}, returned_rows={returned_rows}, matched_symbols={matched_symbols}, affected_symbols={affected_symbols}, exception_type={exception_type}, exception_message={exception_message}".format(
                function_name=diagnostic.get("function_name", "yfinance.Ticker"),
                status=_provider_health_status(diagnostic),
                returned_rows=diagnostic.get("returned_rows", ""),
                matched_symbols=record.symbol if record.price is not None else "",
                affected_symbols=record.symbol,
                exception_type=diagnostic.get("exception_type", ""),
                exception_message=diagnostic.get("exception_message", ""),
            )
        )
        if "yfinance" in _minute_bar_attempted_set(record):
            lines.append(
                "- function_name=yfinance.history, status={status}, yfinance_ticker={ticker}, count={count}, reason={reason}, exception_type={exception_type}, exception_message={message}".format(
                    status=_yfinance_minute_status(record),
                    ticker=_minute_note_value(record, "yfinance_ticker") or record.yfinance_ticker,
                    count=record.minute_bar_count if record.minute_bar_provider == "yfinance" else 0,
                    reason=_yfinance_minute_reason(record),
                    exception_type=_minute_note_value(record, "yfinance_error_type"),
                    message=_minute_note_value(record, "yfinance_error_message"),
                )
            )
    return lines


def _eastmoney_direct_health_group(records: list[PriceRecord]) -> list[str]:
    eastmoney_records = [
        record
        for record in records
        if record.source == "eastmoney_direct"
        or record.selected_provider == "eastmoney_direct"
        or _record_has_attempt_function(record, ["eastmoney_direct.stock_get"])
    ]
    if not eastmoney_records:
        return ["- provider: eastmoney_direct", "- market_category: ETF/A_SHARE", "- status: not_called"]
    lines = [
        "- provider: eastmoney_direct",
        "- market_category: ETF/A_SHARE",
        f"- affected_symbols: {_symbols(eastmoney_records)}",
        f"- quote_time_status: {_quote_time_status(eastmoney_records)}",
        f"- usable_for_operation: {_usable_for_operation(eastmoney_records)}",
        "- source_limit_note: Eastmoney Direct uses Eastmoney public web quote endpoint; not an official exchange real-time feed; first version is reference-grade / operation-candidate only.",
    ]
    for record in eastmoney_records:
        diagnostic = _record_provider_attempt(record, "eastmoney_direct.stock_get") or (
            record.provider_diagnostics
            if record.source == "eastmoney_direct" or record.selected_provider == "eastmoney_direct"
            else {}
        )
        if not diagnostic:
            continue
        lines.append(
            "- function_name={function_name}, status={status}, secid={secid}, endpoint={endpoint}, matched_symbols={matched_symbols}, affected_symbols={affected_symbols}, exception_type={exception_type}, exception_message={exception_message}, quote_trust_tier={tier}, usable_for_operation={operation}, confirmation_required={confirmation}".format(
                function_name=diagnostic.get("function_name", "eastmoney_direct.stock_get"),
                status=_provider_health_status(diagnostic),
                secid=diagnostic.get("secid", ""),
                endpoint=diagnostic.get("endpoint", ""),
                matched_symbols=record.symbol if record.price is not None else "",
                affected_symbols=record.symbol,
                exception_type=diagnostic.get("exception_type", ""),
                exception_message=diagnostic.get("exception_message", ""),
                tier=record.quote_trust_tier,
                operation=record.usable_for_operation,
                confirmation=record.confirmation_required,
            )
        )
    return lines


def _mock_health_group(records: list[PriceRecord]) -> list[str]:
    mock_records = [record for record in records if record.source == "mock"]
    if not mock_records:
        return ["- provider: mock", "- status: not_called"]
    return [
        "- provider: mock",
        "- function_name=mock_prices.yaml",
        f"- status: {_records_status(mock_records)}",
        f"- matched_symbols: {_symbols(mock_records)}",
        f"- affected_symbols: {_symbols(mock_records)}",
        f"- quote_time_status: {_quote_time_status(mock_records)}",
        f"- usable_for_operation: {_usable_for_operation(mock_records)}",
    ]


def _provider_attempts_by_symbol(records: list[PriceRecord]) -> list[str]:
    if not records:
        return ["- 无"]
    lines: list[str] = []
    for record in records:
        diagnostic = record.provider_diagnostics
        attempts = diagnostic.get("provider_attempts", []) or diagnostic.get("attempts", [])
        lines.append(f"### {record.symbol}")
        lines.append(f"- provider_policy: {diagnostic.get('provider_policy', '')}")
        lines.append(f"- configured_provider_priority: {_format_symbols(diagnostic.get('configured_provider_priority', []))}")
        lines.append(f"- effective_provider_chain: {_format_symbols(diagnostic.get('effective_provider_chain', diagnostic.get('provider_priority', [])))}")
        lines.append(f"- selected_provider: {diagnostic.get('selected_provider', record.source)}")
        lines.append(f"- selected_source: {diagnostic.get('selected_source', record.source)}")
        lines.append(f"- fallback_used: {diagnostic.get('fallback_used', False)}")
        lines.append(f"- usable_for_operation: {diagnostic.get('usable_for_operation', _record_ok(record))}")
        lines.append(f"- quote_trust_tier: {record.quote_trust_tier}")
        lines.append(f"- usable_for_reference: {record.usable_for_reference}")
        lines.append(f"- confirmation_required: {record.confirmation_required}")
        if record.reference_note:
            lines.append(f"- reference_note: {record.reference_note}")
        lines.append(f"- selection_reason: {diagnostic.get('selection_reason', '')}")
        blocking_reason = _blocking_reason(record)
        lines.append(f"- final_blocking_reason: {blocking_reason}")
        lines.append(f"- reconciliation_enabled: {record.reconciliation_enabled}")
        lines.append(f"- source_agreement_status: {record.source_agreement_status}")
        lines.append(f"- operation_candidate_agreed: {record.operation_candidate_agreed}")
        if not attempts:
            lines.append("- attempts: 无")
            continue
        lines.append("- attempts:")
        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            attempt_is_selected_success = (
                attempt.get("status") == "success"
                and str(attempt.get("provider", "")) == str(diagnostic.get("selected_provider", record.source))
            )
            lines.append(
                "  - provider={provider}, function_name={function_name}, status={status}, secid={secid}, endpoint={endpoint}, request_status={request_status}, retry_count={retry_count}, final_status={final_status}, from_cache={from_cache}, price={price}, quote_time={quote_time}, usable_for_operation={usable_for_operation}, quote_trust_tier={quote_trust_tier}, usable_for_reference={usable_for_reference}, confirmation_required={confirmation_required}, elapsed_seconds={elapsed_seconds}, slow_provider_attempt={slow_provider_attempt}, reason={reason}, exception_type={exception_type}, exception_message={exception_message}".format(
                    provider=attempt.get("provider", ""),
                    function_name=attempt.get("function_name", ""),
                    status=attempt.get("status", ""),
                    secid=attempt.get("secid", ""),
                    endpoint=attempt.get("endpoint", ""),
                    request_status=attempt.get("request_status", ""),
                    retry_count=attempt.get("retry_count", ""),
                    final_status=attempt.get("final_status", ""),
                    from_cache=attempt.get("from_cache", ""),
                    price=attempt.get("price", ""),
                    quote_time=attempt.get("quote_time", ""),
                    usable_for_operation=attempt.get("usable_for_operation", ""),
                    quote_trust_tier=attempt.get("quote_trust_tier", record.quote_trust_tier if attempt_is_selected_success else ""),
                    usable_for_reference=attempt.get("usable_for_reference", record.usable_for_reference if attempt_is_selected_success else ""),
                    confirmation_required=attempt.get("confirmation_required", record.confirmation_required if attempt_is_selected_success else ""),
                    elapsed_seconds=attempt.get("elapsed_seconds", ""),
                    slow_provider_attempt=attempt.get("slow_provider_attempt", ""),
                    reason=attempt.get("reason", ""),
                    exception_type=attempt.get("exception_type", ""),
                    exception_message=attempt.get("exception_message", ""),
                )
            )
    return lines


def _runtime_freshness_lines(runtime: dict[str, Any]) -> list[str]:
    lines = [
        "- 详见 runtime_diagnostics.md",
        f"- provider_policy: {runtime.get('provider_policy', '')}",
        f"- total_elapsed_seconds: {runtime.get('total_elapsed_seconds', '')}",
        f"- run_time_budget_exceeded: {runtime.get('run_time_budget_exceeded', False)}",
        f"- max_quote_lag_seconds: {runtime.get('max_quote_lag_seconds', '')}",
        f"- max_data_lag_seconds: {runtime.get('max_data_lag_seconds', '')}",
    ]
    if runtime.get("run_time_budget_exceeded"):
        lines.append("- 本轮刷新耗时超过预算，价格不宜用于盘中精确做T或高频操作。")
    return lines


def _files_for_profile(runtime: dict[str, Any]) -> set[str]:
    common = {
        "index.md",
        "prices_snapshot.csv",
        "data_completeness_report.md",
        "provider_health_report.md",
        "runtime_diagnostics.md",
        "price_reconciliation_report.md",
        "provider_capability_report.md",
    }
    universe_type = str(runtime.get("universe_type", ""))
    if universe_type == "candidate_watchlist":
        return {*common, "candidate_watchlist_report.md"}
    if universe_type == "scan_universe":
        return {*common, "scan_universe_report.md"}
    if universe_type == "operation_candidate":
        return {*common, "operation_candidate_report.md"}
    profile = str(runtime.get("profile", "all"))
    if profile == "tech" and str(runtime.get("reconcile_mode", "")) == "full":
        return {*common, "tech_price_block.md"}
    if runtime.get("provider_policy") == "diagnostic":
        return common
    if profile == "tech":
        return {*common, "tech_price_block.md"}
    if profile == "energy":
        return {*common, "energy_price_block.md"}
    if profile in {"all", "controller"}:
        return {*common, "controller_price_summary.md"}
    return common


def _remove_unscoped_outputs(output_dir: Path, emit_files: set[str]) -> None:
    managed = {
        "energy_price_block.md",
        "tech_price_block.md",
        "controller_price_summary.md",
        "candidate_watchlist_report.md",
        "scan_universe_report.md",
        "operation_candidate_report.md",
        "unsupported_symbols_report.md",
        "minute_bars_snapshot.csv",
    }
    for filename in managed - emit_files:
        path = output_dir / filename
        if path.exists():
            path.unlink()


def _provider_call_summary_lines(records: list[PriceRecord]) -> list[str]:
    attempts = [attempt for attempt in _all_provider_attempts(records) if attempt.get("provider") == "akshare"]
    if not attempts:
        return ["- 无"]
    grouped: dict[str, list[dict[str, object]]] = {}
    for attempt in attempts:
        function_name = str(attempt.get("function_name", ""))
        if function_name:
            grouped.setdefault(function_name, []).append(attempt)
    lines: list[str] = []
    for function_name, function_attempts in sorted(grouped.items()):
        call_ids = {
            str(attempt.get("call_id"))
            for attempt in function_attempts
            if attempt.get("call_id") not in {"", None} and not attempt.get("from_cache")
        }
        if not call_ids:
            call_ids = {
                str(attempt.get("call_id"))
                for attempt in function_attempts
                if attempt.get("call_id") not in {"", None}
            }
        first = function_attempts[0]
        matched_symbols = _format_symbols(
            sorted({str(attempt.get("symbol", "")) for attempt in function_attempts if attempt.get("status") == "success"})
        )
        lines.append(
            "- function_name={function_name}, call_count={call_count}, cache_hits={cache_hits}, returned_rows={returned_rows}, matched_symbols={matched_symbols}, elapsed_seconds_first_call={elapsed}, failed={failed}, exception_type={exception_type}, exception_message={exception_message}".format(
                function_name=function_name,
                call_count=len(call_ids),
                cache_hits=sum(1 for attempt in function_attempts if attempt.get("from_cache")),
                returned_rows=first.get("returned_rows", ""),
                matched_symbols=matched_symbols,
                elapsed=first.get("elapsed_seconds_first_call", ""),
                failed=not any(attempt.get("status") == "success" for attempt in function_attempts),
                exception_type=first.get("exception_type", ""),
                exception_message=first.get("exception_message", ""),
            )
        )
    return lines


def _runtime_provider_cache_lines(records: list[PriceRecord]) -> list[str]:
    attempts = [attempt for attempt in _all_provider_attempts(records) if attempt.get("provider") == "akshare"]
    if not attempts:
        return [
            "- total_provider_calls: 0",
            "- cache_hits: 0",
            "- provider_call_count_by_function: 无",
        ]
    grouped: dict[str, set[str]] = {}
    for attempt in attempts:
        function_name = str(attempt.get("function_name", ""))
        call_id = str(attempt.get("call_id", ""))
        if function_name and call_id and not attempt.get("from_cache"):
            grouped.setdefault(function_name, set()).add(call_id)
    lines = [
        f"- total_provider_calls: {sum(len(call_ids) for call_ids in grouped.values())}",
        f"- cache_hits: {sum(1 for attempt in attempts if attempt.get('from_cache'))}",
        "- provider_call_count_by_function:",
    ]
    for function_name, call_ids in sorted(grouped.items()):
        lines.append(f"  - {function_name}: {len(call_ids)}")
        if len(call_ids) > 1:
            lines.append(f"  - warning: {function_name} called more than once")
    return lines


def _index_issue_counts(records: list[PriceRecord], summary: CompletenessSummary, runtime: dict[str, Any]) -> dict[str, int]:
    attempts = _all_provider_attempts(records)
    return {
        "blocking_records": len(summary.strict_blockers),
        "provider_error": sum(1 for record in records if "provider_error" in record.quality_issues),
        "stale": len(summary.stale_prices),
        "quote_time_missing": len(summary.quote_time_missing),
        "mock_fallback_not_usable": sum(1 for record in records if "mock_fallback_not_allowed" in record.quality_issues),
        "slow_provider_attempts": sum(1 for attempt in attempts if attempt.get("slow_provider_attempt")),
        "fallback_used": sum(1 for record in records if record.provider_diagnostics.get("fallback_used")),
        "run_time_budget_exceeded": 1 if runtime.get("run_time_budget_exceeded") else 0,
    }


def _index_blocking_lines(blockers: list[dict[str, Any]]) -> list[str]:
    return [
        "- project={project}, symbol={symbol}, name={name}, selected_provider={source}, blocking_reason={blocking_reason}, stale_reason={stale_reason}, quote_time={quote_time}".format(
            **blocker
        )
        for blocker in blockers
    ]


def _coverage_summary_lines(records: list[PriceRecord], profile: str) -> list[str]:
    return [
        f"- 能源账户核心价格：{_project_coverage(records, 'energy', profile)}",
        f"- 科技账户核心价格：{_project_coverage(records, 'tech', profile)}",
        f"- 黄金参考价：{_symbol_coverage(records, 'GOLD_CNY', profile)}",
        f"- 非科技宽基：{_symbol_coverage(records, '510300.SH', profile)}",
    ]


def _quote_trust_summary_lines(records: list[PriceRecord], quote_purpose: str) -> list[str]:
    counts = _quote_trust_counts(records)
    confirmation_required = sum(1 for record in records if record.confirmation_required)
    usable_for_reference = bool(records) and any(record.usable_for_reference for record in records)
    usable_for_operation = False if quote_purpose == "reference" else build_completeness_summary(records).usable_for_operation
    return [
        f"- current quote_purpose: {quote_purpose or 'operation'}",
        f"- operation-grade records 数量: {counts.get('operation', 0)}",
        f"- reference-grade records 数量: {counts.get('reference', 0)}",
        f"- development-grade records 数量: {counts.get('development', 0)}",
        f"- confirmation_required 数量: {confirmation_required}",
        f"- 可用于快速参考: {_yes_no(usable_for_reference)}",
        f"- 可用于具体操作建议: {_yes_no(usable_for_operation)}",
    ]


def _quote_trust_diagnostic_lines(records: list[PriceRecord]) -> list[str]:
    if not records:
        return ["- 无"]
    counts = _quote_trust_counts(records)
    lines = [
        f"- quote_purpose: {records[0].quote_purpose if records else 'operation'}",
        f"- quote_trust_tier summary: operation={counts.get('operation', 0)}, reference={counts.get('reference', 0)}, development={counts.get('development', 0)}",
        f"- operation-grade records: {_format_symbols([record.symbol for record in records if record.quote_trust_tier == 'operation'])}",
        f"- reference-grade records: {_format_symbols([record.symbol for record in records if record.quote_trust_tier == 'reference'])}",
        f"- development-grade records: {_format_symbols([record.symbol for record in records if record.quote_trust_tier == 'development'])}",
        f"- confirmation_required records: {_format_symbols([record.symbol for record in records if record.confirmation_required])}",
    ]
    if any(record.quote_purpose == "reference" for record in records):
        lines.append("- operation confirmation required: reference-grade records are not operation-grade permission.")
    yfinance_records = [record for record in records if record.source == "yfinance" or record.selected_provider == "yfinance"]
    if yfinance_records:
        lines.append(
            "- yfinance source limitation: open-source Yahoo Finance public API wrapper; research/educational use; not official exchange feed; use together with quote_time, freshness, and usable_for_operation."
        )
    eastmoney_records = [record for record in records if record.source == "eastmoney_direct" or record.selected_provider == "eastmoney_direct"]
    if eastmoney_records:
        lines.append(
            "- eastmoney_direct source limitation: Eastmoney public web quote endpoint; reference / operation-candidate only in this version; not operation-grade by itself."
        )
    return lines


def _quote_trust_counts(records: list[PriceRecord]) -> dict[str, int]:
    counts = {"operation": 0, "reference": 0, "development": 0}
    for record in records:
        tier = record.quote_trust_tier or "development"
        counts[tier] = counts.get(tier, 0) + 1
    return counts


def _usage_level(records: list[PriceRecord], summary: CompletenessSummary, runtime: dict[str, Any]) -> str:
    if runtime.get("provider_policy") == "diagnostic":
        return "diagnostic-only"
    if runtime.get("quote_purpose") == "reference":
        return "reference-only"
    required = [record for record in records if record.required_for_operation]
    operation_ready = (
        summary.usable_for_operation
        and all(record.quote_trust_tier == "operation" for record in required)
        and all(record.usable_for_operation for record in required)
        and not any(record.confirmation_required for record in required)
    )
    return "operation-ready" if operation_ready else "operation-blocked"


def _invalid_price_count(records: list[PriceRecord]) -> int:
    return sum(1 for record in records if record.price is None or "invalid_price" in record.quality_issues)


def _quote_trust_bundle_lines(records: list[PriceRecord]) -> list[str]:
    counts = _quote_trust_counts(records)
    return [
        f"- operation-grade records 数量: {counts.get('operation', 0)}",
        f"- reference-grade records 数量: {counts.get('reference', 0)}",
        f"- development-grade records 数量: {counts.get('development', 0)}",
        f"- usable_for_reference=true 数量: {sum(1 for record in records if record.usable_for_reference)}",
        f"- usable_for_operation=true 数量: {sum(1 for record in records if record.usable_for_operation)}",
        f"- confirmation_required=true 数量: {sum(1 for record in records if record.confirmation_required)}",
    ]


def _reconciliation_summary_lines(records: list[PriceRecord]) -> list[str]:
    summary = reconciliation_summary(records)
    lines = [
        "- reconciliation_enabled: true",
        f"- source_agreement_status summary: aligned={summary.get('aligned', 0)}, minor_diff={summary.get('minor_diff', 0)}, warning_diff={summary.get('warning_diff', 0)}, major_diff={summary.get('major_diff', 0)}, single_source_only={summary.get('single_source_only', 0)}, insufficient_data={summary.get('insufficient_data', 0)}, provider_error={summary.get('provider_error', 0)}",
        f"- operation_candidate_agreed count: {sum(1 for record in records if record.operation_candidate_agreed)}",
        "- multi-source reconciliation is diagnostic only and does not upgrade reference-grade to operation-grade.",
        "- full report: price_reconciliation_report.md",
        "- upload: daily use should start with 0_upload_bundle.md; add debug_bundle.md only for blocking, provider_error, stale, quote_time_missing, major_diff, or runtime budget issues.",
    ]
    if summary.get("major_diff", 0):
        lines.append("- major_diff present: review debug_bundle.md and price_reconciliation_report.md.")
    return lines


def _reconciliation_detail_lines(records: list[PriceRecord]) -> list[str]:
    scoped = [record for record in records if record.reconciliation_enabled]
    if not scoped:
        return ["- reconciliation_enabled: true", "- status: insufficient_data", "- full report: price_reconciliation_report.md"]
    lines = ["- full report: price_reconciliation_report.md"]
    for record in scoped:
        lines.append(
            "- {symbol}: compared_sources={sources}, source_agreement_status={status}, price_diff_pct={pct}, quote_time_gap_seconds={gap}, operation_candidate_agreed={agreed}, note={note}".format(
                symbol=record.symbol,
                sources=record.compared_sources,
                status=record.source_agreement_status,
                pct="" if record.price_diff_pct is None else record.price_diff_pct,
                gap="" if record.quote_time_gap_seconds is None else record.quote_time_gap_seconds,
                agreed=record.operation_candidate_agreed,
                note=record.reconciliation_note,
            )
        )
    return lines


def _bundle_project_lines(records: list[PriceRecord], profile: str, provider_policy: str, universe_type: str = "") -> list[str]:
    if universe_type == "candidate_watchlist":
        return ["### Candidate watchlist", "", *build_candidate_watchlist_report(records, {}).splitlines()[2:]]
    if universe_type == "scan_universe":
        return ["### Scan universe", "", *build_scan_universe_report(records, {}).splitlines()[2:]]
    if universe_type == "operation_candidate":
        return ["### Operation candidates", "", *build_operation_candidate_report(records, {}).splitlines()[2:]]
    if provider_policy == "diagnostic":
        return [
            "- 当前用途级别：diagnostic-only",
            "- 诊断输出用于排查 provider / runtime / freshness / blocking 问题，不直接作为项目操作依据。",
        ]
    if profile == "tech":
        lines: list[str] = []
        for title, asset_role in TECH_GROUPS:
            grouped = [record for record in records if record.project == "tech" and record.asset_role == asset_role]
            lines.extend([f"### {title}", ""])
            lines.extend(_price_table(grouped))
            lines.append("")
        return lines
    if profile == "energy":
        energy_records = [record for record in records if record.project == "energy"]
        return ["### 能源账户核心价格", "", *_price_table(energy_records)]
    if profile in {"all", "controller"}:
        return ["### 总控摘要", "", *build_controller_summary(records).splitlines()[2:]]
    return ["- 无"]


def _bundle_usage_note_lines(quote_purpose: str, usage_level: str) -> list[str]:
    if quote_purpose == "reference":
        return [
            "- 本轮为快速参考模式。",
            "- 可以用于快速参考。",
            "- 不可用于具体操作建议。",
            "- 不可给出具体执行动作、盘中高频判断或挂单参数。",
            "- 如需具体操作，请运行 operation 输出或补充有效盘口信息。",
        ]
    if usage_level == "operation-ready":
        return [
            "- 本轮为 operation 模式。",
            "- strict=0 且 operation-grade 条件通过，可进入完整操作级分析。",
        ]
    return [
        "- 本轮为 operation 模式。",
        "- 如果 strict=2 或 blocking records 存在，不得给高精度执行价位。",
        "- 可根据数据完整度要求补充数据或降级为事实核对。",
    ]


def _debug_snapshot_table(records: list[PriceRecord]) -> list[str]:
    lines = [
        "| symbol | name | selected_provider/source | quote_purpose | quote_trust_tier | usable_for_reference | usable_for_operation | confirmation_required | price | currency | quote_time | is_stale | stale_reason | required_for_operation | operation_blocking_reason | reference_note |",
        "|---|---|---|---|---|---|---|---|---:|---|---|---|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            "| {symbol} | {name} | {provider} | {quote_purpose} | {tier} | {reference} | {operation} | {confirmation} | {price} | {currency} | {quote_time} | {stale} | {stale_reason} | {required} | {blocking} | {note} |".format(
                symbol=record.symbol,
                name=record.name,
                provider=record.selected_provider or record.source,
                quote_purpose=record.quote_purpose,
                tier=record.quote_trust_tier,
                reference=record.usable_for_reference,
                operation=record.usable_for_operation,
                confirmation=record.confirmation_required,
                price="" if record.price is None else record.price,
                currency=record.currency,
                quote_time=record.quote_time.isoformat() if record.quote_time else "",
                stale=record.is_stale,
                stale_reason=record.stale_reason,
                required=record.required_for_operation,
                blocking=record.operation_blocking_reason,
                note=record.reference_note,
            )
        )
    if not records:
        lines.append("|  |  |  |  |  |  |  |  |  |  |  |  | 无 |  |  |  |")
    return lines


def _sanitize_bundle_text(text: str) -> str:
    replacements = {
        "买入": "具体执行动作",
        "卖出": "具体执行动作",
        "加仓": "仓位动作",
        "减仓": "仓位动作",
        "做T": "盘中高频判断",
        "目标价": "执行价格",
        "挂单价": "挂单参数",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _project_coverage(records: list[PriceRecord], project: str, profile: str) -> str:
    if profile in {"energy", "tech"} and profile != project:
        return "本轮未刷新"
    project_records = [record for record in records if record.project == project and record.required_for_operation]
    if not project_records:
        return "本轮未刷新"
    return "完整" if all(_record_ok(record) for record in project_records) else "不完整"


def _symbol_coverage(records: list[PriceRecord], symbol: str, profile: str) -> str:
    if profile == "energy" and symbol in {"GOLD_CNY", "510300.SH"}:
        return "本轮未刷新"
    record = next((item for item in records if item.symbol == symbol), None)
    if record is None:
        return "本轮未刷新"
    return "可用" if _record_ok(record) else "不可用"


def _selected_provider_counts(records: list[PriceRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        provider = str(record.provider_diagnostics.get("selected_provider") or record.source or "unknown")
        counts[provider] = counts.get(provider, 0) + 1
    return counts


def _provider_call_total(records: list[PriceRecord]) -> int:
    call_ids = {
        str(attempt.get("call_id"))
        for attempt in _all_provider_attempts(records)
        if attempt.get("provider") == "akshare" and attempt.get("call_id") not in {"", None} and not attempt.get("from_cache")
    }
    return len(call_ids)


def _provider_cache_hits(records: list[PriceRecord]) -> int:
    return sum(
        1
        for attempt in _all_provider_attempts(records)
        if attempt.get("provider") == "akshare" and attempt.get("from_cache")
    )


def _recommended_files(profile: str, provider_policy: str) -> list[str]:
    return ["0_upload_bundle.md", "debug_bundle.md if blocking/provider_error/stale/quote_time_missing/major_diff/runtime issues appear"]


def _oldest_quote_time(records: list[PriceRecord]) -> str:
    quote_times = [record.quote_time for record in records if record.quote_time is not None]
    return min(quote_times).isoformat() if quote_times else ""


def _newest_quote_time(records: list[PriceRecord]) -> str:
    quote_times = [record.quote_time for record in records if record.quote_time is not None]
    return max(quote_times).isoformat() if quote_times else ""


def _all_provider_attempts(records: list[PriceRecord]) -> list[dict[str, object]]:
    attempts: list[dict[str, object]] = []
    for record in records:
        provider_attempts = record.provider_diagnostics.get("provider_attempts", []) or []
        if provider_attempts:
            for attempt in provider_attempts:
                if isinstance(attempt, dict):
                    attempts.append(attempt)
            continue
        for attempt in record.provider_diagnostics.get("attempts", []) or []:
            if isinstance(attempt, dict):
                attempts.append({"symbol": record.symbol, "provider": record.source, **attempt})
    return attempts


def _per_provider_elapsed(attempts: list[dict[str, object]]) -> dict[str, float]:
    elapsed: dict[str, float] = {}
    for attempt in attempts:
        provider = str(attempt.get("provider", ""))
        if not provider:
            continue
        elapsed[provider] = round(elapsed.get(provider, 0.0) + float(attempt.get("elapsed_seconds") or 0.0), 3)
    return elapsed


def _per_symbol_elapsed(records: list[PriceRecord]) -> dict[str, float]:
    elapsed: dict[str, float] = {}
    for record in records:
        total = 0.0
        for attempt in record.provider_diagnostics.get("provider_attempts", []) or []:
            if isinstance(attempt, dict):
                total += float(attempt.get("elapsed_seconds") or 0.0)
        elapsed[record.symbol] = round(total, 3)
    return elapsed


def _provider_routing_note_lines(records: list[PriceRecord]) -> list[str]:
    notes: list[str] = []
    for record in records:
        diagnostics = record.provider_diagnostics
        if diagnostics.get("provider_policy"):
            notes.append(f"- {record.symbol}: provider_policy={diagnostics.get('provider_policy')}")
        if diagnostics.get("fallback_used"):
            notes.append(
                f"- {record.symbol}: primary failed but fallback selected; selected_provider={diagnostics.get('selected_provider', '')}; selection_reason={diagnostics.get('selection_reason', '')}"
            )
        if diagnostics.get("selected_provider") == "yfinance":
            notes.append(
                f"- {record.symbol}: 使用 yfinance secondary provider；数据源限制：open-source Yahoo Finance public API wrapper; research/educational use; not official exchange feed"
            )
        if diagnostics.get("selected_provider") == "eastmoney_direct":
            notes.append(
                f"- {record.symbol}: 使用 eastmoney_direct reference provider；source limitation: Eastmoney public web quote endpoint, not official exchange real-time feed; first version is reference-grade / operation-candidate only"
            )
        if "mock_fallback_not_allowed" in record.quality_issues:
            notes.append(f"- {record.symbol}: mock fallback 不可用于具体操作建议")
        if "manual_fallback_not_allowed" in record.quality_issues:
            notes.append(f"- {record.symbol}: manual fallback 未配置为可用于具体操作建议")
    if not notes:
        return ["- 无"]
    return notes


def _provider_health_status(diagnostic: dict[str, object]) -> str:
    provider_status = str(diagnostic.get("provider_status", ""))
    if provider_status in {"fallback_success", "fallback_failed"}:
        return provider_status
    status = str(diagnostic.get("status", ""))
    if status == "fail":
        return "failed"
    if status == "success":
        return "success"
    return status or "unknown"


def _provider_policy_from_records(records: list[PriceRecord]) -> str:
    for record in records:
        policy = record.provider_diagnostics.get("provider_policy")
        if policy:
            return str(policy)
    return ""


def _quote_purpose_from_records(records: list[PriceRecord]) -> str:
    for record in records:
        purpose = record.provider_diagnostics.get("quote_purpose") or record.quote_purpose
        if purpose:
            return str(purpose)
    return "operation"


def _records_status(records: list[PriceRecord]) -> str:
    if not records:
        return "not_called"
    if all(_record_ok(record) for record in records):
        return "success"
    if any(_record_ok(record) for record in records):
        return "partial_success"
    return "failed"


def _usable_for_operation(records: list[PriceRecord]) -> str:
    required = [record for record in records if record.required_for_operation]
    candidates = required or records
    if not candidates:
        return "no"
    ok_count = sum(1 for record in candidates if _record_ok(record))
    if ok_count == len(candidates):
        return "yes"
    if ok_count:
        return "partial"
    return "no"


def _quote_time_status(records: list[PriceRecord]) -> str:
    if not records:
        return "not_available"
    statuses = set()
    for record in records:
        issues = set(record.quality_issues)
        if "invalid_quote_time" in issues:
            statuses.add("invalid")
        elif record.quote_time is None or "quote_time_missing" in issues:
            statuses.add("missing")
        elif record.is_stale:
            statuses.add("stale")
        else:
            statuses.add("ok")
    if len(statuses) == 1:
        return next(iter(statuses))
    return "mixed:" + ",".join(sorted(statuses))


def _symbols(records: list[PriceRecord]) -> str:
    return _format_symbols([record.symbol for record in records])


def _format_symbols(symbols: object) -> str:
    if not symbols:
        return ""
    if isinstance(symbols, str):
        return symbols
    if isinstance(symbols, list | tuple | set):
        return ", ".join(str(symbol) for symbol in symbols)
    return str(symbols)


def _group_provider_diagnostics(records: list[PriceRecord]) -> dict[str, dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for record in records:
        diagnostic = record.provider_diagnostics
        for attempt in diagnostic.get("attempts", []) or []:
            if isinstance(attempt, dict):
                _merge_provider_diagnostic(grouped, attempt)
        for attempt in diagnostic.get("provider_attempts", []) or []:
            if isinstance(attempt, dict):
                _merge_provider_diagnostic(grouped, attempt)
        if diagnostic.get("function_name"):
            _merge_provider_diagnostic(grouped, diagnostic)
    return grouped


def _merge_provider_diagnostic(grouped: dict[str, dict[str, object]], diagnostic: dict[str, object]) -> None:
        function_name = str(diagnostic.get("function_name", ""))
        if not function_name:
            return
        existing = grouped.get(function_name)
        if existing is None:
            grouped[function_name] = dict(diagnostic)
            return
        if existing.get("status") != "fail" and diagnostic.get("status") == "fail":
            grouped[function_name] = dict(diagnostic)
            return
        if existing.get("status") == "success" and diagnostic.get("status") == "success":
            existing_symbols = list(existing.get("matched_symbols", []) or [])
            new_symbols = list(diagnostic.get("matched_symbols", []) or [])
            existing["matched_symbols"] = list(dict.fromkeys(existing_symbols + new_symbols))
            if diagnostic.get("provider_status") == "fallback_success":
                existing["provider_status"] = "fallback_success"


def _record_has_attempt_function(record: PriceRecord, function_names: list[str]) -> bool:
    wanted = set(function_names)
    for attempt in record.provider_diagnostics.get("provider_attempts", []) or []:
        if isinstance(attempt, dict) and attempt.get("function_name") in wanted:
            return True
    return False


def _record_provider_attempt(record: PriceRecord, function_name: str) -> dict[str, object] | None:
    for attempt in record.provider_diagnostics.get("provider_attempts", []) or []:
        if isinstance(attempt, dict) and attempt.get("function_name") == function_name:
            return attempt
    for attempt in record.provider_diagnostics.get("attempts", []) or []:
        if isinstance(attempt, dict) and attempt.get("function_name") == function_name:
            return attempt
    diagnostic = record.provider_diagnostics
    if diagnostic.get("function_name") == function_name:
        return diagnostic
    return None


def _akshare_freshness_lines(records: list[PriceRecord]) -> list[str]:
    if not records:
        return ["- 无"]
    lines = []
    for record in records:
        diagnostic = record.provider_diagnostics
        lines.append(
            "- {symbol}: market_status={market_status}, quote_time_raw={quote_time_raw}, quote_time_utc={quote_time_utc}, fetch_time_utc={fetch_time_utc}, age_seconds={age_seconds}, max_age_seconds={max_age_seconds}, is_stale={is_stale}".format(
                symbol=record.symbol,
                market_status=record.market_status,
                quote_time_raw=diagnostic.get("quote_time_raw", ""),
                quote_time_utc=diagnostic.get("quote_time_utc", ""),
                fetch_time_utc=diagnostic.get("fetch_time_utc", ""),
                age_seconds=diagnostic.get("age_seconds", ""),
                max_age_seconds=diagnostic.get("max_age_seconds", ""),
                is_stale=record.is_stale,
            )
        )
        if record.market_status == "closed":
            lines.append(f"- {record.symbol}: market_status=closed, 市场已收盘，价格为收盘后/最后更新时间参考，不适合盘中做T判断")
    return lines


def _price_table(records: list[PriceRecord]) -> list[str]:
    lines = [
        "| symbol | name | price | currency | source | selected_provider | quote_time | fetch_time | market_status | is_stale | stale_reason | usable_for_operation | quote_trust_tier | usable_for_reference | confirmation_required |",
        "|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            "| {symbol} | {name} | {price} | {currency} | {source} | {selected_provider} | {quote_time} | {fetch_time} | {market_status} | {is_stale} | {stale_reason} | {usable_for_operation} | {quote_trust_tier} | {usable_for_reference} | {confirmation_required} |".format(
                symbol=record.symbol,
                name=record.name,
                price="" if record.price is None else record.price,
                currency=record.currency,
                source=record.source,
                selected_provider=record.selected_provider or record.provider_diagnostics.get("selected_provider", record.source),
                quote_time=record.quote_time.isoformat() if record.quote_time else "",
                fetch_time=record.fetch_time.isoformat() if record.fetch_time else "",
                market_status=record.market_status,
                is_stale=record.is_stale,
                stale_reason=record.stale_reason,
                usable_for_operation=record.usable_for_operation,
                quote_trust_tier=record.quote_trust_tier,
                usable_for_reference=record.usable_for_reference,
                confirmation_required=record.confirmation_required,
            )
        )
    if not records:
        lines.append("|  |  |  |  |  |  |  |  |  |  | 无 |  |  |  |  |")
    return lines


def _watchlist_table(records: list[PriceRecord]) -> list[str]:
    lines = [
        "| symbol | name | role | report_group | price | source | quote_time | quote_trust_tier | usable_for_reference | usable_for_operation | confirmation_required | source_agreement_status | data_status | note |",
        "|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|",
    ]
    for record in records:
        data_status = "ok" if _record_ok(record) or record.usable_for_reference else "check_required"
        lines.append(
            "| {symbol} | {name} | {role} | {group} | {price} | {source} | {quote_time} | {tier} | {reference} | {operation} | {confirmation} | {agreement} | {status} | {note} |".format(
                symbol=record.symbol,
                name=record.name,
                role=record.role or record.asset_role or "",
                group=record.report_group,
                price="" if record.price is None else record.price,
                source=record.selected_provider or record.source,
                quote_time=record.quote_time.isoformat() if record.quote_time else "",
                tier=record.quote_trust_tier,
                reference=record.usable_for_reference,
                operation=record.usable_for_operation,
                confirmation=record.confirmation_required,
                agreement=record.source_agreement_status,
                status=data_status,
                note=record.notes or record.reference_note or record.unsupported_reason,
            )
        )
    if not records:
        lines.append("|  |  |  |  |  |  |  |  |  |  |  |  | none |  |")
    return lines


def _base_quote_summary_lines(records: list[PriceRecord]) -> list[str]:
    if not records:
        return ["- base_quote_completeness: none"]
    counts: dict[str, int] = {}
    for record in records:
        key = record.base_quote_completeness or "missing"
        counts[key] = counts.get(key, 0) + 1
    lines = ["- base_quote_completeness counts:"]
    lines.extend([f"- {key}: {value}" for key, value in sorted(counts.items())])
    lines.append(f"- missing fields top: {_base_quote_missing_top(records)}")
    lines.append("- base quote fields are auxiliary diagnostics; missing fields do not change existing strict in this version.")
    return lines


def _base_quote_snapshot_lines(records: list[PriceRecord], profile: str, universe_type: str) -> list[str]:
    if profile in {"all", "controller"}:
        return _base_quote_controller_summary_lines(records)
    if universe_type == "candidate_watchlist":
        lines = _watchlist_base_quote_table(records, scan=False)
        lines.extend(_watchlist_scan_note_lines())
        return lines
    if universe_type == "scan_universe":
        lines = _watchlist_base_quote_table(records, scan=True)
        lines.extend(_watchlist_scan_note_lines())
        return lines
    include_stale = profile == "energy"
    lines = _compact_base_quote_table(records, include_stale=include_stale)
    lines.append("- base_quote_completeness is shown in the compact `base` column.")
    lines.extend(_base_quote_unit_note_lines())
    return lines


def _compact_base_quote_table(records: list[PriceRecord], include_stale: bool = False) -> list[str]:
    stale_header = " | stale?" if include_stale else ""
    stale_sep = "|---" if include_stale else ""
    lines = [
        f"| symbol | name | last | chg% | open | high | low | prev | volume | amount | base | provider | tier | op?{stale_header} |",
        f"|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---{stale_sep}|",
    ]
    for record in records:
        stale_value = f" | {_fmt(record.is_stale)}" if include_stale else ""
        lines.append(
            "| {symbol} | {name} | {last} | {chg} | {open} | {high} | {low} | {prev} | {volume} | {amount} | {base} | {provider} | {tier} | {op}{stale} |".format(
                symbol=record.symbol,
                name=record.name,
                last=_fmt(record.last_price if record.last_price is not None else record.price),
                chg=_fmt(record.price_change_pct),
                open=_fmt(record.open_price),
                high=_fmt(record.high_price),
                low=_fmt(record.low_price),
                prev=_fmt(record.prev_close),
                volume=_fmt(record.volume),
                amount=_fmt(record.amount),
                base=record.base_quote_completeness or "missing",
                provider=record.selected_provider or record.source,
                tier=record.quote_trust_tier,
                op=record.usable_for_operation,
                stale=stale_value,
            )
        )
    if not records:
        lines.append(f"| — | — | — | — | — | — | — | — | — | — | missing | — | — | —{' | —' if include_stale else ''} |")
    return lines


def _watchlist_base_quote_table(records: list[PriceRecord], scan: bool) -> list[str]:
    if scan:
        lines = [
            "| symbol | name | tags | last | chg% | amount | base | data_status | provider | note |",
            "|---|---|---|---:|---:|---:|---|---|---|---|",
        ]
        for record in records:
            lines.append(
                "| {symbol} | {name} | {tags} | {last} | {chg} | {amount} | {base} | {status} | {provider} | {note} |".format(
                    symbol=record.symbol,
                    name=record.name,
                    tags=", ".join(record.universe_tags),
                    last=_fmt(record.last_price if record.last_price is not None else record.price),
                    chg=_fmt(record.price_change_pct),
                    amount=_fmt(record.amount),
                    base=record.base_quote_completeness or "missing",
                    status=_base_quote_data_status(record),
                    provider=record.selected_provider or record.source,
                    note=_base_quote_note(record, scan=True),
                )
            )
        if not records:
            lines.append("| — | — | — | — | — | — | missing | missing | — | scan_only |")
        return lines
    lines = [
        "| symbol | name | last | chg% | high | low | amount | base | data_status | provider | required_for_operation |",
        "|---|---|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            "| {symbol} | {name} | {last} | {chg} | {high} | {low} | {amount} | {base} | {status} | {provider} | {required} |".format(
                symbol=record.symbol,
                name=record.name,
                last=_fmt(record.last_price if record.last_price is not None else record.price),
                chg=_fmt(record.price_change_pct),
                high=_fmt(record.high_price),
                low=_fmt(record.low_price),
                amount=_fmt(record.amount),
                base=record.base_quote_completeness or "missing",
                status=_base_quote_data_status(record),
                provider=record.selected_provider or record.source,
                required=record.required_for_operation,
            )
        )
    if not records:
        lines.append("| — | — | — | — | — | — | — | missing | missing | — | false |")
    return lines


def _operation_candidate_summary_lines(records: list[PriceRecord], runtime: dict[str, Any]) -> list[str]:
    if not records:
        return [
            f"- universe_name: {runtime.get('universe_name', 'tech_operation_candidates')}",
            f"- universe_type: {runtime.get('universe_type', 'operation_candidate')}",
            "- total_candidates: 0",
            "- candidate_data_status: empty_universe",
            "- required_for_operation: false",
            "- usable_for_operation: false",
            "- affect_core_strict: false",
            "- These are pre-trade verification candidates, not core holdings.",
            "- They do not affect tech_fast_strict or outputs_tech_latest.",
            "- Failure in this universe does not block core operation.",
            "- not usable for concrete operation recommendations.",
        ]
    statuses: dict[str, int] = {}
    for record in records:
        status = record.candidate_data_status or "data_incomplete"
        statuses[status] = statuses.get(status, 0) + 1
    return [
        f"- universe_name: {runtime.get('universe_name', 'tech_operation_candidates')}",
        f"- universe_type: {runtime.get('universe_type', 'operation_candidate')}",
        f"- total_candidates: {len(records)}",
        f"- ready_for_review: {statuses.get('ready_for_review', 0)}",
        f"- data_incomplete: {statuses.get('data_incomplete', 0)}",
        f"- provider_error: {statuses.get('provider_error', 0)}",
        f"- symbol_not_found: {statuses.get('symbol_not_found', 0)}",
        f"- registry_missing: {statuses.get('registry_missing', 0)}",
        "- required_for_operation: false",
        "- usable_for_operation: false",
        "- affect_core_strict: false",
        "- not usable for concrete operation recommendations.",
    ]


def _operation_candidate_table(records: list[PriceRecord]) -> list[str]:
    lines = [
        "| symbol | name | operation_candidate | candidate_quote_ready | candidate_data_status | candidate_blocking_reason | candidate_next_step | required_for_operation | affect_core_strict | usable_for_operation | usable_for_reference | provider | rankable | rank_exclusion_reason |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            "| {symbol} | {name} | {candidate} | {ready} | {status} | {reason} | {next_step} | {required} | {affect} | {operation} | {reference} | {provider} | {rankable} | {rank_reason} |".format(
                symbol=record.symbol,
                name=record.name,
                candidate=record.operation_candidate or record.universe_type == "operation_candidate",
                ready=record.candidate_quote_ready,
                status=record.candidate_data_status or "data_incomplete",
                reason=record.candidate_blocking_reason or "none",
                next_step=record.candidate_next_step or "no_action_data_incomplete",
                required=record.required_for_operation,
                affect=record.affect_core_strict,
                operation=record.usable_for_operation,
                reference=record.usable_for_reference,
                provider=record.selected_provider or record.source,
                rankable=record.rankable,
                rank_reason=record.rank_exclusion_reason,
            )
        )
    if not records:
        lines.append("|  |  | true | false | empty_universe | empty_universe | keep_watchlist | false | false | false | false |  | false | empty_universe |")
    return lines


def _base_quote_fields_table(records: list[PriceRecord]) -> list[str]:
    lines = [
        "| symbol | name | last | chg% | open | high | low | prev | volume | amount | base | missing_fields |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for record in records:
        lines.append(
            "| {symbol} | {name} | {last} | {chg} | {open} | {high} | {low} | {prev} | {volume} | {amount} | {base} | {missing} |".format(
                symbol=record.symbol,
                name=record.name,
                last=_fmt(record.last_price if record.last_price is not None else record.price),
                chg=_fmt(record.price_change_pct),
                open=_fmt(record.open_price),
                high=_fmt(record.high_price),
                low=_fmt(record.low_price),
                prev=_fmt(record.prev_close),
                volume=_fmt(record.volume),
                amount=_fmt(record.amount),
                base=record.base_quote_completeness or "missing",
                missing=record.base_quote_missing_fields or "—",
            )
        )
    if not records:
        lines.append("| — | — | — | — | — | — | — | — | — | — | missing | — |")
    return lines


def _base_quote_controller_summary_lines(records: list[PriceRecord]) -> list[str]:
    scopes = {
        "tech_core": [record for record in records if record.project == "tech"],
        "energy_core": [record for record in records if record.project == "energy"],
        "gold": [record for record in records if record.symbol == "GOLD_CNY"],
        "fx_index": [record for record in records if record.symbol in {"USD_CNY", "HKD_CNY", "IXIC"}],
        "scan/watchlist": [record for record in records if record.universe_type in {"candidate_watchlist", "scan_universe"}],
    }
    lines = ["| scope | complete | partial | price_only | missing | note |", "|---|---:|---:|---:|---:|---|"]
    for scope, scoped in scopes.items():
        counts = _base_quote_counts(scoped)
        note = "not refreshed" if not scoped else "summary only"
        lines.append(
            f"| {scope} | {counts.get('complete', 0)} | {counts.get('partial', 0)} | {counts.get('price_only', 0)} | {counts.get('missing', 0)} | {note} |"
        )
    issue_records = [record for record in records if record.base_quote_completeness in {"missing", "price_only"} or record.quality_issues]
    if issue_records:
        lines.extend(["", "| symbol | name | issue | base | provider | note |", "|---|---|---|---|---|---|"])
        for record in issue_records[:12]:
            issue = ",".join(record.quality_issues) or record.base_quote_missing_fields or "base_quote_incomplete"
            lines.append(f"| {record.symbol} | {record.name} | {issue} | {record.base_quote_completeness} | {record.selected_provider or record.source} | summary_only |")
    lines.append("- controller bundle keeps base quote output summarized; project-specific bundles keep detailed symbol tables.")
    return lines


def _base_quote_counts(records: list[PriceRecord]) -> dict[str, int]:
    counts = {"complete": 0, "partial": 0, "price_only": 0, "missing": 0}
    for record in records:
        key = record.base_quote_completeness or "missing"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _base_quote_data_status(record: PriceRecord) -> str:
    issues = set(record.quality_issues)
    if "provider_error" in issues:
        return "provider_error"
    if "symbol_not_found" in issues:
        return "symbol_not_found"
    if record.base_quote_completeness:
        return record.base_quote_completeness
    if record.usable_for_reference:
        return "reference_only"
    return "missing"


def _base_quote_note(record: PriceRecord, scan: bool = False) -> str:
    issues = set(record.quality_issues)
    if "symbol_not_found" in issues:
        return "symbol_not_found"
    if "provider_error" in issues:
        return "provider_error"
    if record.amount_source.endswith("unknown") or record.volume_source.endswith("raw_unit"):
        return "unit_unknown"
    if scan:
        return "scan_only"
    if not record.required_for_operation:
        return "required_for_operation=false"
    if record.quote_trust_tier == "reference":
        return "reference_only"
    return "not_operation_input" if not record.usable_for_operation else "ok"


def _watchlist_scan_note_lines() -> list[str]:
    return [
        "- candidate/watchlist/scan records do not affect core strict.",
        "- symbol_not_found in candidate or scan output is a data coverage status, not a system failure.",
        "- not usable for concrete operation recommendations.",
    ]


def _watchlist_scan_failure_reason_table(records: list[PriceRecord]) -> list[str]:
    lines = [
        "| symbol | registry_found | provider_attempted | provider_status | data_status | likely_reason | suggested_next_step |",
        "|---|---|---|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            "| {symbol} | {registry_found} | {provider_attempted} | {provider_status} | {data_status} | {likely_reason} | {next_step} |".format(
                symbol=record.symbol,
                registry_found=record.registry_found,
                provider_attempted=_provider_attempted(record),
                provider_status=_provider_status(record),
                data_status=_base_quote_data_status(record),
                likely_reason=_likely_reason(record),
                next_step=_suggested_next_step(record),
            )
        )
    if not records:
        lines.append("| none |  |  |  | missing | no_records | no action |")
    return lines


def _provider_attempted(record: PriceRecord) -> str:
    attempts = record.provider_diagnostics.get("provider_attempts", []) or record.provider_diagnostics.get("attempts", [])
    providers = []
    for attempt in attempts:
        if isinstance(attempt, dict) and attempt.get("provider"):
            providers.append(str(attempt.get("provider")))
    if providers:
        return ",".join(dict.fromkeys(providers))
    return record.selected_provider or record.source or "not_attempted"


def _provider_status(record: PriceRecord) -> str:
    diagnostic_status = record.provider_diagnostics.get("provider_status") or record.provider_diagnostics.get("status")
    if diagnostic_status:
        return str(diagnostic_status)
    if record.price is not None and record.quote_time is not None:
        return "success"
    if record.quality_issues:
        return ",".join(record.quality_issues)
    return "unknown"


def _likely_reason(record: PriceRecord) -> str:
    issues = set(record.quality_issues)
    if "symbol_not_found" in issues:
        return "provider_symbol_not_found" if record.registry_found else "unsupported_symbol"
    if "provider_error" in issues:
        return "endpoint_failed"
    if "quote_time_missing" in issues:
        return "quote_time_missing"
    if "invalid_price" in issues:
        return "invalid_price"
    if record.selected_provider in {"mock", "mock_fallback"} or record.source in {"mock", "mock_fallback"}:
        return "mock/development only"
    if record.price is None:
        return "no_reference_provider_success"
    if record.amount_unit == "unit_unknown" or record.volume_unit == "unit_unknown":
        return "unit_unknown"
    return "reference_available" if record.usable_for_reference else "check_required"


def _suggested_next_step(record: PriceRecord) -> str:
    reason = _likely_reason(record)
    if reason in {"provider_symbol_not_found", "unsupported_symbol"}:
        return "validate symbol/provider mapping"
    if reason == "endpoint_failed":
        return "keep as candidate; review provider_health/debug details"
    if reason == "no_reference_provider_success":
        return "try diagnostic provider coverage check"
    if reason == "unit_unknown":
        return "do not use volume/amount for cross-provider ranking"
    if record.universe_type in {"candidate_watchlist", "scan_universe"}:
        return "keep as candidate; does not affect core strict"
    return "review provider_capability_report.md"


def _base_quote_unit_note_lines() -> list[str]:
    return [
        "",
        "- volume/amount follow provider raw units unless unit normalization is explicitly available.",
        "- 成交量/成交额暂按 provider 原始单位展示；未统一单位前不得直接跨 provider 排名。",
    ]


def _base_quote_caveat_lines() -> list[str]:
    return [
        "",
        "### Base quote caveats",
        "- volume/amount follow provider raw units unless unit normalization is explicitly available.",
        "- cross-provider volume/amount comparison is not reliable until provider field validation is completed.",
        "- base quote missing does not change existing strict; base quote and field capability issues do not change existing strict in v0.7.1.6.",
        "- operation still depends on quote_trust_tier / usable_for_operation / strict / freshness.",
        "- field completeness is a diagnostic aid, not trading advice.",
    ]


def _base_quote_field_sources_table(records: list[PriceRecord]) -> list[str]:
    lines = [
        "| symbol | last_source | prev_source | open_source | high_source | low_source | volume_source | amount_source | chg_source | completeness | missing_fields |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            f"| {record.symbol} | {_fmt(record.last_price_source)} | {_fmt(record.prev_close_source)} | {_fmt(record.open_price_source)} | {_fmt(record.high_price_source)} | {_fmt(record.low_price_source)} | {_fmt(record.volume_source)} | {_fmt(record.amount_source)} | {_fmt(record.price_change_pct_source)} | {_fmt(record.base_quote_completeness)} | {_fmt(record.base_quote_missing_fields)} |"
        )
    if not records:
        lines.append("| — | — | — | — | — | — | — | — | — | missing | — |")
    return lines


def _provider_capability_note_lines() -> list[str]:
    return [
        "AKShare:",
        "- base quote fields: supported/partially supported through current normalized fields where provider raw fields are available.",
        "- volume: raw provider unit.",
        "- amount: raw provider unit or unit_unknown.",
        "- bid/ask: not validated.",
        "- turnover_rate: not validated.",
        "- minute_bars: not implemented in current guard provider path; probe status is diagnostic.",
        "",
        "Eastmoney Direct:",
        "- base quote fields: available only when endpoint succeeds.",
        "- trust tier: reference / operation-candidate only.",
        "- stability: unstable in current environment.",
        "- bid/ask: not validated.",
        "- minute_bars: not validated / not implemented.",
        "",
        "yfinance:",
        "- base quote fields: reference-only for current ETF/watchlist usage.",
        "- volume: raw provider unit.",
        "- not operation-grade for A-share ETF operation path.",
        "- timestamp/precision may differ from local exchange feeds.",
        "- minute_bars: not implemented in guard probe path in v0.7.2a.",
        "",
        "manual:",
        "- GOLD_CNY price only.",
        "- base_quote_completeness usually price_only.",
        "- minute_bars: not supported.",
        "",
        "mock:",
        "- development/testing only.",
        "- mock minute bars can be generated for tests when minute probe is enabled.",
        "- not valid for real market decisions.",
    ]


def _provider_capabilities() -> dict[str, Any]:
    if not PROVIDER_CAPABILITIES_PATH.exists():
        return {}
    with PROVIDER_CAPABILITIES_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _capability_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for provider, functions in _provider_capabilities().items():
        if not isinstance(functions, dict):
            continue
        for function_name, config in functions.items():
            if not isinstance(config, dict):
                continue
            entries.append(
                {
                    "provider": str(config.get("provider") or provider),
                    "function_name": str(config.get("function_name") or function_name),
                    "asset_types": config.get("asset_types", []),
                    "operation_fit": str(config.get("operation_fit", "")),
                    "notes": str(config.get("notes", "")),
                    "fields": config.get("fields", {}) if isinstance(config.get("fields", {}), dict) else {},
                }
            )
    return entries


def _provider_capability_summary_table() -> list[str]:
    lines = [
        "| provider | function_name | asset_type | base_price_fields | volume_amount_status | bid_ask_status | turnover_status | minute_status | operation_fit | notes |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for entry in _capability_entries():
        fields = entry["fields"]
        base_status = _combined_field_status(
            fields,
            ["last_price", "prev_close", "open_price", "high_price", "low_price", "price_change_pct", "amplitude_pct"],
        )
        volume_amount = "volume={volume}; amount={amount}".format(
            volume=_capability_field(fields, "volume").get("status", "missing"),
            amount=_capability_field(fields, "amount").get("status", "missing"),
        )
        bid_ask = "bid1={bid}; ask1={ask}".format(
            bid=_capability_field(fields, "bid1_price").get("status", "missing"),
            ask=_capability_field(fields, "ask1_price").get("status", "missing"),
        )
        lines.append(
            "| {provider} | {function} | {asset_types} | {base} | {volume_amount} | {bid_ask} | {turnover} | {minute} | {operation_fit} | {notes} |".format(
                provider=entry["provider"],
                function=entry["function_name"],
                asset_types=", ".join(str(item) for item in entry["asset_types"]),
                base=base_status,
                volume_amount=volume_amount,
                bid_ask=bid_ask,
                turnover=_capability_field(fields, "turnover_rate").get("status", "missing"),
                minute=_capability_field(fields, "minute_bars").get("status", "missing"),
                operation_fit=entry["operation_fit"],
                notes=entry["notes"],
            )
        )
    if len(lines) == 2:
        lines.append("| none | none | none | missing | missing | missing | missing | missing | no | config missing |")
    return lines


def _field_capability_matrix_by_provider() -> list[str]:
    lines = [
        "| provider | function_name | field | status | unit | unit_confidence | comparable_across_providers | operation_fit | reference_fit | notes |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for entry in _capability_entries():
        for field, config in sorted(entry["fields"].items()):
            if not isinstance(config, dict):
                continue
            lines.append(
                "| {provider} | {function} | {field} | {status} | {unit} | {confidence} | {comparable} | {operation} | {reference} | {notes} |".format(
                    provider=entry["provider"],
                    function=entry["function_name"],
                    field=field,
                    status=config.get("status", ""),
                    unit=config.get("unit", ""),
                    confidence=config.get("unit_confidence", ""),
                    comparable=config.get("comparable_across_providers", ""),
                    operation=config.get("operation_fit", ""),
                    reference=config.get("reference_fit", ""),
                    notes=config.get("notes", ""),
                )
            )
    if len(lines) == 2:
        lines.append("| none | none | none | missing |  |  | false | no | false | config missing |")
    return lines


def _symbol_field_quality_table(records: list[PriceRecord]) -> list[str]:
    lines = [
        "| symbol | name | provider | base | volume_unit | amount_unit | volume_comparable | amount_comparable | field_validation_status | notes |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            "| {symbol} | {name} | {provider} | {base} | {volume_unit} | {amount_unit} | {volume_comp} | {amount_comp} | {status} | {notes} |".format(
                symbol=record.symbol,
                name=record.name,
                provider=record.selected_provider or record.source,
                base=record.base_quote_completeness,
                volume_unit=record.volume_unit,
                amount_unit=record.amount_unit,
                volume_comp=record.volume_comparable_across_providers,
                amount_comp=record.amount_comparable_across_providers,
                status=record.field_validation_status,
                notes=record.provider_capability_notes or _likely_reason(record),
            )
        )
    if not records:
        lines.append("| none | none | none | missing | not_applicable | not_applicable | false | false | missing | no records |")
    return lines


def _provider_capability_safe_usage_lines() -> list[str]:
    return [
        "- Provider capability report is diagnostic only.",
        "- Field capability does not upgrade trust tier.",
        "- Field completeness does not imply operation-grade.",
        "- volume/amount must not be compared across providers until unit validation is high.",
        "- bid/ask and turnover are not validated in v0.7.2a.",
        "- minute bars are probe-only in v0.7.2a; VWAP and QDII premium remain not implemented.",
        "- This report is not trading advice.",
    ]


def _minute_probe_visible(records: list[PriceRecord], runtime: dict[str, Any]) -> bool:
    return bool(runtime.get("include_minute_bars")) or any(
        record.minute_bar_status and record.minute_bar_status != "not_attempted" for record in records
    )


def _minute_bars_summary_table(records: list[PriceRecord]) -> list[str]:
    lines = [
        "| symbol | name | available | provider | interval | count | latest_time | status | validation | note |",
        "|---|---|---|---|---|---:|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            "| {symbol} | {name} | {available} | {provider} | {interval} | {count} | {latest} | {status} | {validation} | {note} |".format(
                symbol=record.symbol,
                name=record.name,
                available=record.minute_bars_available,
                provider=_fmt(record.minute_bar_provider),
                interval=_fmt(record.minute_bar_interval),
                count=record.minute_bar_count,
                latest=_fmt(record.minute_bar_latest_time),
                status=_fmt(record.minute_bar_status),
                validation=_fmt(record.minute_bar_validation_status),
                note=_fmt(_minute_bar_upload_note(record)),
            )
        )
    if not records:
        lines.append("| none | none | false | missing | not_available | 0 | - | missing | missing | no records |")
    return lines


def _minute_bars_probe_note_lines() -> list[str]:
    return [
        "- Minute bars are diagnostic in v0.7.2a.2b.",
        "- Minute bars do not change strict or operation readiness in this version.",
        "- VWAP and intraday derived fields are not calculated in v0.7.2a.",
        "- Operation decisions still depend on quote_trust_tier / usable_for_operation / strict / freshness.",
        "- This section does not provide execution instructions.",
    ]


def _minute_bars_detail_table(records: list[PriceRecord]) -> list[str]:
    lines = [
        "| symbol | provider_attempted | provider_success | normalized_symbol | eastmoney_secid | akshare_status | akshare_reason | akshare_error_type | akshare_error_message | eastmoney_status | eastmoney_reason | eastmoney_endpoint | eastmoney_error_type | eastmoney_error_message | yfinance_ticker | yfinance_status | yfinance_reason | yfinance_error_type | yfinance_error_message | status | interval | count | latest_time | fetch_time | validation_status | missing_reason | market_session | after_close_possible | after_close_applies_to | retry_suggested | retry_reason | notes |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            "| {symbol} | {provider} | {success} | {normalized} | {secid} | {ak_status} | {ak_reason} | {ak_type} | {ak_message} | {east_status} | {east_reason} | {east_endpoint} | {east_type} | {east_message} | {yf_ticker} | {yf_status} | {yf_reason} | {yf_type} | {yf_message} | {status} | {interval} | {count} | {latest} | {fetch} | {validation} | {reason} | {session} | {after_close} | {applies_to} | {retry} | {retry_reason} | {notes} |".format(
                symbol=record.symbol,
                provider=_fmt(_minute_bar_provider_attempted(record)),
                success=_fmt(record.minute_bar_provider if record.minute_bars_available else "none"),
                normalized=_fmt(_minute_bar_normalized_symbol(record)),
                secid=_fmt(_eastmoney_secid_from_record(record)),
                ak_status=_fmt(_akshare_minute_status(record)),
                ak_reason=_fmt(_akshare_minute_reason(record)),
                ak_type=_fmt(_minute_note_value(record, "akshare_error_type")),
                ak_message=_fmt(_minute_note_value(record, "akshare_error_message")),
                east_status=_fmt(_minute_note_value(record, "eastmoney_status")),
                east_reason=_fmt(_minute_note_value(record, "eastmoney_reason")),
                east_endpoint=_fmt(_minute_note_value(record, "eastmoney_endpoint")),
                east_type=_fmt(_minute_note_value(record, "eastmoney_error_type")),
                east_message=_fmt(_minute_note_value(record, "eastmoney_error_message")),
                yf_ticker=_fmt(_minute_note_value(record, "yfinance_ticker") or record.yfinance_ticker),
                yf_status=_fmt(_minute_note_value(record, "yfinance_status")),
                yf_reason=_fmt(_minute_note_value(record, "yfinance_reason")),
                yf_type=_fmt(_minute_note_value(record, "yfinance_error_type")),
                yf_message=_fmt(_minute_note_value(record, "yfinance_error_message")),
                status=_fmt(record.minute_bar_status),
                interval=_fmt(record.minute_bar_interval),
                count=record.minute_bar_count,
                latest=_fmt(record.minute_bar_latest_time),
                fetch=_fmt(record.minute_bar_fetch_time),
                validation=_fmt(record.minute_bar_validation_status),
                reason=_fmt(record.minute_bar_missing_reason),
                session=_fmt(record.minute_bar_market_session),
                after_close=record.minute_bar_after_close_possible,
                applies_to=_fmt(record.minute_bar_after_close_applies_to or _minute_note_value(record, "after_close_applies_to")),
                retry=_fmt(record.minute_bar_retry_suggested),
                retry_reason=_fmt(record.minute_bar_retry_reason),
                notes=_fmt(record.minute_bar_notes),
            )
        )
    if not records:
        lines.append("| none | missing | none | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | missing | not_available | 0 | - | - | missing | no_records | - | false | - | - | - | no records |")
    return lines


def _minute_bars_completeness_lines(records: list[PriceRecord], runtime: dict[str, Any]) -> list[str]:
    statuses = _minute_bar_status_counts(records)
    providers = _minute_bar_provider_counts(records)
    akshare_attempted = [record for record in records if "akshare" in _minute_bar_attempted_set(record)]
    eastmoney_attempted = [record for record in records if "eastmoney_direct" in _minute_bar_attempted_set(record)]
    yfinance_attempted = [record for record in records if "yfinance" in _minute_bar_attempted_set(record)]
    session_counts: dict[str, int] = {}
    for record in records:
        session = record.minute_bar_market_session or "missing"
        session_counts[session] = session_counts.get(session, 0) + 1
    lines = [
        f"- include_minute_bars: {runtime.get('include_minute_bars', False)}",
        f"- minute_bars_available count: {sum(1 for record in records if record.minute_bars_available)}",
        f"- unavailable count: {statuses.get('unavailable', 0)}",
        f"- not_supported count: {statuses.get('not_supported', 0)}",
        f"- provider_error count: {statuses.get('provider_error', 0)}",
        f"- symbol_not_found count: {statuses.get('symbol_not_found', 0)}",
        f"- stale count: {statuses.get('stale', 0)}",
        f"- akshare_attempted_count: {len(akshare_attempted)}",
        f"- akshare_success_count: {sum(1 for record in akshare_attempted if _akshare_minute_status(record) == 'available')}",
        f"- akshare_error_count: {sum(1 for record in akshare_attempted if _akshare_minute_status(record) == 'provider_error')}",
        f"- yfinance_attempted_count: {len(yfinance_attempted)}",
        f"- yfinance_success_count: {sum(1 for record in yfinance_attempted if _yfinance_minute_status(record) == 'available')}",
        f"- yfinance_error_count: {sum(1 for record in yfinance_attempted if _yfinance_minute_status(record) in {'provider_error', 'parse_error'})}",
        f"- yfinance_empty_response_count: {sum(1 for record in yfinance_attempted if _yfinance_minute_reason(record) == 'empty_response')}",
        f"- yfinance_parse_error_count: {sum(1 for record in yfinance_attempted if _yfinance_minute_reason(record) == 'parse_error')}",
        f"- eastmoney_attempted_count: {len(eastmoney_attempted)}",
        f"- eastmoney_success_count: {sum(1 for record in eastmoney_attempted if _eastmoney_minute_status(record) == 'available')}",
        f"- eastmoney_error_count: {sum(1 for record in eastmoney_attempted if _eastmoney_minute_status(record) in {'provider_error', 'parse_error'})}",
        f"- eastmoney_empty_response_count: {sum(1 for record in eastmoney_attempted if _eastmoney_minute_reason(record) == 'empty_response')}",
        f"- eastmoney_parse_error_count: {sum(1 for record in eastmoney_attempted if _eastmoney_minute_reason(record) == 'parse_error')}",
        f"- empty_response count: {sum(1 for record in records if record.minute_bar_missing_reason == 'empty_response')}",
        f"- after_close_possible_count: {sum(1 for record in records if record.minute_bar_after_close_possible)}",
        f"- retry_during_trading_hours_count: {sum(1 for record in records if record.minute_bar_retry_suggested == 'rerun_during_cn_trading_hours')}",
        "- current session summary: " + (", ".join(f"{key}:{value}" for key, value in sorted(session_counts.items())) if session_counts else "none"),
        "- upload bundle uses compact minute notes; full provider diagnostics remain in debug_bundle.md.",
        "- status counts:",
    ]
    lines.extend([f"  - {status}: {count}" for status, count in sorted(statuses.items())] or ["  - none: 0"])
    lines.append("- by provider:")
    lines.extend([f"  - {provider}: {count}" for provider, count in sorted(providers.items())] or ["  - none: 0"])
    lines.extend(
        [
            "- minute bars missing does not change existing strict in v0.7.2a.2.",
            "- Eastmoney minute bars are diagnostic/reference only.",
            "- VWAP / intraday position fields are not implemented.",
            "- minute bars are diagnostic only.",
        ]
    )
    return lines


def _minute_bars_capability_lines(records: list[PriceRecord], runtime: dict[str, Any]) -> list[str]:
    lines = [
        f"- include_minute_bars: {runtime.get('include_minute_bars', False)}",
        "- akshare: ETF minute bars attempted through fund_etf_hist_min_em when --include-minute-bars is enabled.",
        "- eastmoney_direct: minute bars attempted as diagnostic fallback; provider_dependent and not operation-grade.",
        "- yfinance: attempted_reference_fallback / provider_dependent_reference after AKShare and Eastmoney fail; not operation-grade.",
        "- manual: not_supported.",
        "- mock: supported_for_tests when --include-minute-bars is used with provider-mode=mock.",
    ]
    lines.extend(_minute_bars_completeness_lines(records, runtime))
    return lines


def _minute_bar_status_counts(records: list[PriceRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        status = record.minute_bar_status or "missing"
        counts[status] = counts.get(status, 0) + 1
    return counts


def _minute_bar_normalized_symbol(record: PriceRecord) -> str:
    if record.symbol.endswith((".SH", ".SZ", ".HK")):
        return record.symbol.split(".")[0]
    return record.symbol


def _minute_bar_provider_attempted(record: PriceRecord) -> str:
    notes = record.minute_bar_notes or ""
    marker = "provider_attempted="
    if marker in notes:
        value = notes.split(marker, 1)[1].split(";", 1)[0].strip()
        if value:
            return value
    return record.minute_bar_provider or "missing"


def _minute_bar_upload_note(record: PriceRecord) -> str:
    if record.minute_bar_upload_note:
        return record.minute_bar_upload_note[:120]
    if record.minute_bars_available:
        interval = record.minute_bar_interval or "minute"
        if record.minute_bar_provider == "akshare":
            return f"akshare_{interval}_ok; diagnostic_only"
        if record.minute_bar_provider == "eastmoney_direct":
            return f"eastmoney_{interval}_ok; diagnostic_only; not_operation_grade"
        if record.minute_bar_provider == "yfinance":
            if record.minute_bar_after_close_possible:
                return "yf_ref_ok; ak/em after_close_possible; provider_dependent; not_operation_grade"
            return "yf_ref_ok; provider_dependent; not_operation_grade"
    if record.minute_bar_provider == "manual" and record.minute_bar_missing_reason == "manual_price_only":
        return "manual_price_only; minute_not_supported"
    if "yfinance" in _minute_bar_attempted_set(record):
        return "all_minute_providers_failed; see_debug"
    if record.minute_bar_status == "not_attempted":
        return "minute_probe_not_enabled"
    return f"{record.minute_bar_status or 'minute_unavailable'}; see_debug"


def _minute_bar_attempted_set(record: PriceRecord) -> set[str]:
    return {item.strip() for item in _minute_bar_provider_attempted(record).split(",") if item.strip()}


def _minute_note_value(record: PriceRecord, key: str) -> str:
    notes = record.minute_bar_notes or ""
    marker = f"{key}="
    if marker not in notes:
        return ""
    return notes.split(marker, 1)[1].split(";", 1)[0].strip()


def _akshare_minute_status(record: PriceRecord) -> str:
    status = _minute_note_value(record, "akshare_status")
    if status:
        return status
    if record.minute_bar_provider == "akshare":
        return record.minute_bar_status or "missing"
    return "not_called"


def _akshare_minute_reason(record: PriceRecord) -> str:
    reason = _minute_note_value(record, "akshare_reason")
    if reason:
        return reason
    if record.minute_bar_provider == "akshare":
        return record.minute_bar_missing_reason or ""
    return ""


def _eastmoney_minute_status(record: PriceRecord) -> str:
    status = _minute_note_value(record, "eastmoney_status")
    if status:
        return status
    if record.minute_bar_provider == "eastmoney_direct":
        return record.minute_bar_status or "missing"
    return "not_called"


def _eastmoney_minute_reason(record: PriceRecord) -> str:
    reason = _minute_note_value(record, "eastmoney_reason")
    if reason:
        return reason
    if record.minute_bar_provider == "eastmoney_direct":
        return record.minute_bar_missing_reason or ""
    return ""


def _yfinance_minute_status(record: PriceRecord) -> str:
    status = _minute_note_value(record, "yfinance_status")
    if status:
        return status
    if record.minute_bar_provider == "yfinance":
        return record.minute_bar_status or "missing"
    return "not_called"


def _yfinance_minute_reason(record: PriceRecord) -> str:
    reason = _minute_note_value(record, "yfinance_reason")
    if reason:
        return reason
    if record.minute_bar_provider == "yfinance":
        return record.minute_bar_missing_reason or ""
    return ""


def _eastmoney_secid_from_record(record: PriceRecord) -> str:
    notes = record.minute_bar_notes or ""
    marker = "eastmoney_secid="
    if marker in notes:
        value = notes.split(marker, 1)[1].split(";", 1)[0].strip()
        if value:
            return value
    if record.symbol.endswith(".SH"):
        return f"1.{record.symbol.split('.')[0]}"
    if record.symbol.endswith(".SZ"):
        return f"0.{record.symbol.split('.')[0]}"
    return ""


def _minute_bar_provider_counts(records: list[PriceRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        provider = record.minute_bar_provider or "missing"
        counts[provider] = counts.get(provider, 0) + 1
    return counts


def _field_quality_note_lines() -> list[str]:
    return [
        "- volume/amount are shown in provider raw units unless explicitly validated.",
        "- cross-provider volume/amount comparison is unsafe in this version.",
        "- bid/ask, turnover_rate, minute_bars, VWAP and QDII premium are not validated or not implemented.",
        "- See debug_bundle.md and provider_capability_report.md for details.",
    ]


def _field_quality_risk_lines(records: list[PriceRecord]) -> list[str]:
    raw_units = sum(
        1
        for record in records
        if record.volume_unit == "raw_provider_unit" or record.amount_unit == "raw_provider_unit"
    )
    unknown_units = sum(1 for record in records if record.volume_unit == "unit_unknown" or record.amount_unit == "unit_unknown")
    non_comparable_volume = sum(1 for record in records if not record.volume_comparable_across_providers)
    non_comparable_amount = sum(1 for record in records if not record.amount_comparable_across_providers)
    return [
        "",
        "### Current field quality risks",
        f"- raw_provider_unit records: {raw_units}",
        f"- unit_unknown records: {unknown_units}",
        f"- volume_comparable_across_providers=false records: {non_comparable_volume}",
        f"- amount_comparable_across_providers=false records: {non_comparable_amount}",
        "- bid/ask not validated; turnover_rate not validated; minute_bars/VWAP/QDII premium not implemented.",
    ]


def _field_quality_capability_lines(records: list[PriceRecord]) -> list[str]:
    volume_comparable_count = sum(1 for record in records if record.volume_comparable_across_providers)
    amount_comparable_count = sum(1 for record in records if record.amount_comparable_across_providers)
    unit_unknown_count = sum(1 for record in records if "unit_unknown" in {record.volume_unit, record.amount_unit})
    raw_unit_count = sum(1 for record in records if "raw_provider_unit" in {record.volume_unit, record.amount_unit})
    status_counts: dict[str, int] = {}
    for record in records:
        status = record.field_validation_status or "missing"
        status_counts[status] = status_counts.get(status, 0) + 1
    lines = [
        f"- volume_comparable_across_providers=true records: {volume_comparable_count}",
        f"- amount_comparable_across_providers=true records: {amount_comparable_count}",
        f"- unit_unknown records: {unit_unknown_count}",
        f"- raw_provider_unit records: {raw_unit_count}",
        "- field_validation_status counts: "
        + (", ".join(f"{key}:{value}" for key, value in sorted(status_counts.items())) if status_counts else "none"),
        "- not_validated fields: bid1_price, ask1_price, turnover_rate",
        "- not_implemented fields: minute_bars, intraday_vwap, iopv, premium_pct",
        "- field validation issues do not change existing strict in v0.7.1.6.",
        "- operation still depends on quote_trust_tier / usable_for_operation / strict / freshness.",
        "- capability data is diagnostic, not trading advice.",
    ]
    return lines


def _capability_field(fields: dict[str, Any], field: str) -> dict[str, Any]:
    value = fields.get(field, {})
    return value if isinstance(value, dict) else {}


def _combined_field_status(fields: dict[str, Any], names: list[str]) -> str:
    statuses = {_capability_field(fields, name).get("status", "missing") for name in names}
    statuses.discard("")
    if not statuses:
        return "missing"
    if len(statuses) == 1:
        return str(next(iter(statuses)))
    if statuses <= {"supported", "supported_or_calculable", "calculable"}:
        return "supported_or_calculable"
    return "mixed:" + ",".join(sorted(str(status) for status in statuses))


def _ranking_records(records: list[PriceRecord]) -> list[PriceRecord]:
    return [record for record in records if record.universe_type in {"candidate_watchlist", "scan_universe"}]


def _ranked_records(records: list[PriceRecord]) -> list[PriceRecord]:
    return sorted(
        [record for record in _ranking_records(records) if record.rankable and record.scan_score_basic is not None],
        key=lambda record: (-(record.scan_score_basic or 0), record.symbol),
    )


def _scan_priority_summary_table(records: list[PriceRecord]) -> list[str]:
    scoped = _ranking_records(records)
    counts = _scan_priority_counts(scoped)
    return [
        "| priority | count | note |",
        "|---|---:|---|",
        f"| high | {counts.get('high', 0)} | review candidates only |",
        f"| medium | {counts.get('medium', 0)} | reference candidates |",
        f"| low | {counts.get('low', 0)} | weak or incomplete |",
        f"| not_rankable | {counts.get('not_rankable', 0)} | data unavailable / provider issue |",
    ]


def _top_scan_candidates_table(records: list[PriceRecord], limit: int = 5) -> list[str]:
    ranked = _ranked_records(records)[:limit]
    lines = [
        "| rank | symbol | name | score | priority | chg% | base | provider | note |",
        "|---:|---|---|---:|---|---:|---|---|---|",
    ]
    for idx, record in enumerate(ranked, start=1):
        lines.append(
            f"| {idx} | {record.symbol} | {record.name} | {_fmt(record.scan_score_basic)} | {record.watch_priority} | {_fmt(record.price_change_pct)} | {record.base_quote_completeness} | {record.selected_provider or record.source} | {record.scan_score_notes} |"
        )
    if not ranked:
        lines.append("|  |  |  |  | not_rankable |  | missing |  | no rankable records |")
    return lines


def _watchlist_review_priority_table(records: list[PriceRecord]) -> list[str]:
    scoped = _ranking_records(records) or records
    lines = [
        "| priority | symbol | name | score | status | last | chg% | base | provider | note |",
        "|---|---|---|---:|---|---:|---:|---|---|---|",
    ]
    for record in sorted(scoped, key=lambda item: (item.watch_priority == "not_rankable", -(item.scan_score_basic or -1), item.symbol)):
        lines.append(
            f"| {record.watch_priority or 'not_rankable'} | {record.symbol} | {record.name} | {_fmt(record.scan_score_basic)} | {record.scan_status or 'not_rankable'} | {_fmt(record.last_price if record.last_price is not None else record.price)} | {_fmt(record.price_change_pct)} | {record.base_quote_completeness} | {record.selected_provider or record.source} | {record.scan_score_notes or record.rank_exclusion_reason} |"
        )
    if not scoped:
        lines.append("| not_rankable |  |  |  | not_rankable |  |  | missing |  | no records |")
    return lines


def _scan_basic_ranking_table(records: list[PriceRecord]) -> list[str]:
    lines = [
        "| rank | symbol | name | tags | score | priority | last | chg% | base | data_quality | momentum | field_quality | liquidity | reconciliation | provider | status | note |",
        "|---:|---|---|---|---:|---|---:|---:|---|---:|---:|---:|---:|---:|---|---|---|",
    ]
    ranked = _ranked_records(records)
    for idx, record in enumerate(ranked, start=1):
        lines.append(
            "| {rank} | {symbol} | {name} | {tags} | {score} | {priority} | {last} | {chg} | {base} | {data} | {momentum} | {field} | {liquidity} | {recon} | {provider} | {status} | {note} |".format(
                rank=idx,
                symbol=record.symbol,
                name=record.name,
                tags=", ".join(record.universe_tags),
                score=_fmt(record.scan_score_basic),
                priority=record.watch_priority,
                last=_fmt(record.last_price if record.last_price is not None else record.price),
                chg=_fmt(record.price_change_pct),
                base=record.base_quote_completeness,
                data=_fmt(record.data_quality_score),
                momentum=_fmt(record.momentum_score_basic),
                field=_fmt(record.field_reliability_score),
                liquidity=_fmt(record.liquidity_score_basic),
                recon=_fmt(record.reconciliation_score),
                provider=record.selected_provider or record.source,
                status=record.scan_status,
                note=record.scan_score_notes,
            )
        )
    if not ranked:
        lines.append("|  |  |  |  |  | not_rankable |  |  | missing |  |  |  |  |  |  | not_rankable | no rankable records |")
    return lines


def _not_rankable_table(records: list[PriceRecord]) -> list[str]:
    scoped = [record for record in _ranking_records(records) if not record.rankable]
    lines = [
        "| symbol | name | reason | provider_status | suggested_next_step |",
        "|---|---|---|---|---|",
    ]
    for record in scoped:
        lines.append(
            f"| {record.symbol} | {record.name} | {record.rank_exclusion_reason or 'not_rankable'} | {_provider_status(record)} | {_suggested_next_step(record)} |"
        )
    if not scoped:
        lines.append("|  |  | none |  |  |")
    return lines


def _scan_ranking_summary_lines(records: list[PriceRecord]) -> list[str]:
    scoped = _ranking_records(records)
    counts = _scan_priority_counts(scoped)
    exclusion_counts: dict[str, int] = {}
    for record in scoped:
        reason = record.rank_exclusion_reason or "none"
        if not record.rankable:
            exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1
    provider_issue_count = sum(1 for record in scoped if record.scan_status == "provider_issue")
    data_insufficient_count = sum(1 for record in scoped if record.scan_status == "data_insufficient")
    return [
        f"- total_symbols: {len(scoped)}",
        f"- rankable_count: {sum(1 for record in scoped if record.rankable)}",
        f"- not_rankable_count: {counts.get('not_rankable', 0)}",
        f"- high_priority_count: {counts.get('high', 0)}",
        f"- medium_priority_count: {counts.get('medium', 0)}",
        f"- low_priority_count: {counts.get('low', 0)}",
        f"- symbol_not_found_count: {exclusion_counts.get('symbol_not_found', 0)}",
        f"- provider_issue_count: {provider_issue_count}",
        f"- data_insufficient_count: {data_insufficient_count}",
        "- exclusion reasons: "
        + (", ".join(f"{key}:{value}" for key, value in sorted(exclusion_counts.items())) if exclusion_counts else "none"),
        "- ranking does not affect strict.",
    ]


def _scan_priority_counts(records: list[PriceRecord]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0, "not_rankable": 0}
    for record in records:
        key = record.watch_priority or "not_rankable"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _scan_ranking_trace_table(records: list[PriceRecord]) -> list[str]:
    scoped = _ranking_records(records)
    lines = [
        "| symbol | rankable | exclusion_reason | data_quality_inputs | momentum_inputs | field_quality_inputs | liquidity_inputs | reconciliation_inputs | final_score | priority | notes |",
        "|---|---|---|---|---|---|---|---|---:|---|---|",
    ]
    for record in scoped:
        lines.append(
            "| {symbol} | {rankable} | {reason} | base={base}; stale={stale}; reference={reference} | price_change_pct={chg} | status={field_status}; provider_capability={capability} | volume_comp={volume_comp}; amount_comp={amount_comp}; volume_unit={volume_unit}; amount_unit={amount_unit} | agreement={agreement} | {score} | {priority} | {notes} |".format(
                symbol=record.symbol,
                rankable=record.rankable,
                reason=record.rank_exclusion_reason or "none",
                base=record.base_quote_completeness,
                stale=record.is_stale,
                reference=record.usable_for_reference,
                chg=_fmt(record.price_change_pct),
                field_status=record.field_validation_status,
                capability=record.provider_capability_status,
                volume_comp=record.volume_comparable_across_providers,
                amount_comp=record.amount_comparable_across_providers,
                volume_unit=record.volume_unit,
                amount_unit=record.amount_unit,
                agreement=record.source_agreement_status,
                score=_fmt(record.scan_score_basic),
                priority=record.watch_priority or "not_rankable",
                notes=record.scan_score_notes,
            )
        )
    if not scoped:
        lines.append("|  | false | not_applicable |  |  |  |  |  |  | not_rankable | scan ranking not applicable for operation profile |")
    return lines


def _scan_ranking_safety_lines() -> list[str]:
    return [
        "",
        "- Scan ranking is not trading advice.",
        "- Reference-only does not mean operation-ready.",
        "- Operation decisions require operation-grade guard output.",
        "- Candidate/watchlist/scan records do not affect core strict.",
        "- volume/amount unit normalization is not complete.",
        "- minute bars / VWAP / QDII premium are not implemented.",
    ]


def _fmt(value: object) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _base_quote_completeness_lines(records: list[PriceRecord]) -> list[str]:
    lines = _base_quote_summary_lines(records)
    lines.extend(["", "| symbol | base_quote_completeness | available | missing | missing_fields |", "|---|---|---:|---:|---|"])
    for record in records:
        lines.append(
            f"| {record.symbol} | {record.base_quote_completeness} | {record.base_quote_fields_available_count} | {record.base_quote_fields_missing_count} | {record.base_quote_missing_fields} |"
        )
    if not records:
        lines.append("|  | none | 0 | 0 |  |")
    return lines


def _base_quote_detail_table(records: list[PriceRecord]) -> list[str]:
    lines = [
        "| symbol | last | prev_close | open | high | low | volume | amount | change | change_pct | amplitude_pct | completeness | missing_fields | field_sources | exchange | country_market | trading_calendar |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---|",
    ]
    for record in records:
        sources = ",".join(
            item
            for item in [
                f"last={record.last_price_source}",
                f"prev={record.prev_close_source}",
                f"open={record.open_price_source}",
                f"high={record.high_price_source}",
                f"low={record.low_price_source}",
                f"volume={record.volume_source}",
                f"amount={record.amount_source}",
                f"change_pct={record.price_change_pct_source}",
            ]
            if not item.endswith("=")
        )
        lines.append(
            "| {symbol} | {last} | {prev} | {open} | {high} | {low} | {volume} | {amount} | {change} | {change_pct} | {amplitude} | {complete} | {missing} | {sources} | {exchange} | {country} | {calendar} |".format(
                symbol=record.symbol,
                last="" if record.last_price is None else record.last_price,
                prev="" if record.prev_close is None else record.prev_close,
                open="" if record.open_price is None else record.open_price,
                high="" if record.high_price is None else record.high_price,
                low="" if record.low_price is None else record.low_price,
                volume="" if record.volume is None else record.volume,
                amount="" if record.amount is None else record.amount,
                change="" if record.price_change is None else record.price_change,
                change_pct="" if record.price_change_pct is None else record.price_change_pct,
                amplitude="" if record.amplitude_pct is None else record.amplitude_pct,
                complete=record.base_quote_completeness,
                missing=record.base_quote_missing_fields,
                sources=sources,
                exchange=record.exchange,
                country=record.country_market,
                calendar=record.trading_calendar,
            )
        )
    if not records:
        lines.append("|  |  |  |  |  |  |  |  |  |  |  | none |  |  |  |  |  |")
    return lines


def _base_quote_missing_top(records: list[PriceRecord]) -> str:
    counts: dict[str, int] = {}
    for record in records:
        for field in (record.base_quote_missing_fields or "").split(","):
            if not field:
                continue
            counts[field] = counts.get(field, 0) + 1
    if not counts:
        return "none"
    return ", ".join(f"{field}:{count}" for field, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:8])


def _universe_isolation_lines(runtime: dict[str, Any]) -> list[str]:
    universe_type = str(runtime.get("universe_type", ""))
    if universe_type in {"candidate_watchlist", "scan_universe", "operation_candidate"}:
        return [
            f"- universe_name: {runtime.get('universe_name', '')}",
            f"- universe_type: {universe_type}",
            "- core strict pollution isolation: enabled",
            "- this universe is not used for core operation strict blocking.",
            "- not usable for concrete operation recommendations.",
        ]
    if universe_type:
        return [
            f"- universe_name: {runtime.get('universe_name', '')}",
            f"- universe_type: {universe_type}",
            "- candidate/watchlist/scan symbols keep required_for_operation=false unless promoted to core_holdings.",
        ]
    return ["- legacy profile mode; no explicit universe selected."]


def _registry_resolution_lines(runtime: dict[str, Any]) -> list[str]:
    if not runtime.get("registry_enabled"):
        return ["- registry_enabled: false"]
    lines = [
        "- registry_enabled: true",
        f"- registry_path: {runtime.get('registry_path', '')}",
        f"- universe_name: {runtime.get('universe_name', '')}",
        f"- universe_type: {runtime.get('universe_type', '')}",
        f"- core_count: {runtime.get('core_count', '')}",
        f"- watchlist_count: {runtime.get('watchlist_count', '')}",
        f"- scan_count: {runtime.get('scan_count', '')}",
        f"- operation_candidate_count: {runtime.get('operation_candidate_count', '')}",
        f"- unsupported_count: {runtime.get('unsupported_count', '')}",
    ]
    unsupported = runtime.get("unsupported_symbols", []) or []
    if unsupported:
        lines.append("- unsupported symbols:")
        for item in unsupported:
            if isinstance(item, dict):
                lines.append(f"  - {item.get('symbol', '')}: {item.get('reason', '')}; suggested_fix={item.get('suggested_fix', '')}")
    return lines


def _bullet_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- 无"]
    return [f"- {item}" for item in items]


def _record_lines(records: list[PriceRecord], marker: str | None = None) -> list[str]:
    if not records:
        return ["- 无"]
    prefix = f"{marker}: " if marker else ""
    return [f"- {prefix}{record.project} {record.symbol} {record.name}: {record.stale_reason}" for record in records]


def _quality_issue_lines(records: list[PriceRecord]) -> list[str]:
    issue_records = [record for record in records if record.quality_issues]
    if not issue_records:
        return ["- 无"]
    return [
        f"- {record.project} {record.symbol} {record.name}: {', '.join(record.quality_issues)}"
        for record in issue_records
    ]


def _manual_record_lines(records: list[PriceRecord]) -> list[str]:
    if not records:
        return ["- 无"]
    lines = []
    for record in records:
        lines.append(
            "- {symbol} {name}: price={price}, quote_time={quote_time}, is_stale={is_stale}, source_note={source_note}, fee_note={fee_note}, asset_role={asset_role}".format(
                symbol=record.symbol,
                name=record.name,
                price="" if record.price is None else record.price,
                quote_time=record.quote_time.isoformat() if record.quote_time else "",
                is_stale=record.is_stale,
                source_note=record.source_note or "",
                fee_note=record.fee_note or "",
                asset_role=record.asset_role or "",
            )
        )
    return lines
