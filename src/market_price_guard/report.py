from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .models import PriceRecord


OUTPUT_COLUMNS = [
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


def write_outputs(records: list[PriceRecord], output_dir: Path, provider_mode: str = "mock") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = records_to_dataframe(records)
    df.to_csv(output_dir / "prices_snapshot.csv", index=False, encoding="utf-8-sig")
    (output_dir / "data_completeness_report.md").write_text(build_completeness_report(records), encoding="utf-8")
    (output_dir / "provider_health_report.md").write_text(
        build_provider_health_report(records, provider_mode=provider_mode),
        encoding="utf-8",
    )
    (output_dir / "energy_price_block.md").write_text(build_project_block(records, "energy", "能源账户价格事实块"), encoding="utf-8")
    (output_dir / "tech_price_block.md").write_text(build_tech_block(records), encoding="utf-8")
    (output_dir / "controller_price_summary.md").write_text(build_controller_summary(records), encoding="utf-8")


def build_completeness_report(records: list[PriceRecord]) -> str:
    summary = build_completeness_summary(records)
    usable_text = "是" if summary.usable_for_operation else "否"
    lines = [
        "# 数据完整度报告",
        "",
        f"可用于具体操作建议：{usable_text}",
        "",
        "本工具不做自动交易，不输出买卖建议，只输出价格事实、数据源、时间戳、市场状态和数据完整度。",
        "",
        "行情源健康状态详见 provider_health_report.md。",
        "",
        "## Strict blocking records",
    ]
    lines.extend(_blocking_record_lines(summary.strict_blockers))
    lines.extend(["", "## Provider diagnostics"])
    lines.extend(_provider_diagnostics_lines(summary.akshare_records))
    lines.extend(["", "## Provider routing notes"])
    lines.extend(_provider_routing_note_lines(records))
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
    lines = [
        "# Provider Health Report",
        "",
        "行情源健康报告仅用于解释价格事实、接口状态和数据完整度，不提供买卖建议，不做自动交易。",
    ]
    lines.extend(["", "## AKShare ETF"])
    lines.extend(_akshare_health_group(records, "ETF", ["fund_etf_spot_em"]))
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
    lines.extend(["", "## Manual"])
    lines.extend(_manual_health_group(records))
    if provider_mode == "mock":
        lines.extend(["", "## Mock"])
        lines.extend(_mock_health_group(records))
    lines.extend(["", "## Provider attempts by symbol"])
    lines.extend(_provider_attempts_by_symbol(records))
    return "\n".join(lines) + "\n"


def build_project_block(records: list[PriceRecord], project: str, title: str) -> str:
    project_records = [record for record in records if record.project == project]
    lines = [f"# {title}", "", "仅为价格事实和新鲜度记录，不包含买卖建议。", ""]
    lines.extend(_price_table(project_records))
    return "\n".join(lines) + "\n"


def build_tech_block(records: list[PriceRecord]) -> str:
    project_records = [record for record in records if record.project == "tech"]
    lines = ["# 科技账户价格事实块", "", "仅为价格事实和新鲜度记录，不包含买卖建议。"]
    for title, asset_role in TECH_GROUPS:
        grouped = [record for record in project_records if record.asset_role == asset_role]
        lines.extend(["", f"## {title}"])
        if asset_role == "defense_or_potential_tech_funding":
            lines.append(GOLD_NOTE)
        lines.extend(_price_table(grouped))
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
    yfinance_records = [record for record in records if record.source == "yfinance"]
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
        diagnostic = record.provider_diagnostics
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
        attempts = diagnostic.get("provider_attempts", [])
        lines.append(f"### {record.symbol}")
        lines.append(f"- provider_priority_chain: {_format_symbols(diagnostic.get('provider_priority', []))}")
        lines.append(f"- selected_provider: {diagnostic.get('selected_provider', record.source)}")
        lines.append(f"- selected_source: {diagnostic.get('selected_source', record.source)}")
        lines.append(f"- fallback_used: {diagnostic.get('fallback_used', False)}")
        lines.append(f"- usable_for_operation: {diagnostic.get('usable_for_operation', _record_ok(record))}")
        lines.append(f"- selection_reason: {diagnostic.get('selection_reason', '')}")
        blocking_reason = _blocking_reason(record)
        lines.append(f"- final_blocking_reason: {blocking_reason}")
        if not attempts:
            lines.append("- attempts: 无")
            continue
        lines.append("- attempts:")
        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            lines.append(
                "  - provider={provider}, function_name={function_name}, status={status}, price={price}, quote_time={quote_time}, usable_for_operation={usable_for_operation}, reason={reason}, exception_type={exception_type}, exception_message={exception_message}".format(
                    provider=attempt.get("provider", ""),
                    function_name=attempt.get("function_name", ""),
                    status=attempt.get("status", ""),
                    price=attempt.get("price", ""),
                    quote_time=attempt.get("quote_time", ""),
                    usable_for_operation=attempt.get("usable_for_operation", ""),
                    reason=attempt.get("reason", ""),
                    exception_type=attempt.get("exception_type", ""),
                    exception_message=attempt.get("exception_message", ""),
                )
            )
    return lines


def _provider_routing_note_lines(records: list[PriceRecord]) -> list[str]:
    notes: list[str] = []
    for record in records:
        diagnostics = record.provider_diagnostics
        if diagnostics.get("fallback_used"):
            notes.append(
                f"- {record.symbol}: primary failed but fallback selected; selected_provider={diagnostics.get('selected_provider', '')}; selection_reason={diagnostics.get('selection_reason', '')}"
            )
        if diagnostics.get("selected_provider") == "yfinance":
            notes.append(
                f"- {record.symbol}: 使用 yfinance secondary provider；数据源限制：open-source Yahoo Finance public API wrapper; research/educational use; not official exchange feed"
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
        "| symbol | name | price | currency | source | quote_time | fetch_time | market_status | is_stale | stale_reason |",
        "|---|---|---:|---|---|---|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            "| {symbol} | {name} | {price} | {currency} | {source} | {quote_time} | {fetch_time} | {market_status} | {is_stale} | {stale_reason} |".format(
                symbol=record.symbol,
                name=record.name,
                price="" if record.price is None else record.price,
                currency=record.currency,
                source=record.source,
                quote_time=record.quote_time.isoformat() if record.quote_time else "",
                fetch_time=record.fetch_time.isoformat() if record.fetch_time else "",
                market_status=record.market_status,
                is_stale=record.is_stale,
                stale_reason=record.stale_reason,
            )
        )
    if not records:
        lines.append("|  |  |  |  |  |  |  |  |  | 无 |")
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
