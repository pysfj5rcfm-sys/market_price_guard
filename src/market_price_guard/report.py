from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True)
class CompletenessSummary:
    usable_for_operation: bool
    reasons: list[str]
    missing_prices: list[PriceRecord]
    stale_prices: list[PriceRecord]
    quote_time_missing: list[PriceRecord]
    strict_blockers: list[PriceRecord]


def build_completeness_summary(records: list[PriceRecord]) -> CompletenessSummary:
    missing_prices = [record for record in records if record.price is None]
    quote_time_missing = [record for record in records if record.quote_time is None]
    stale_prices = [record for record in records if record.is_stale and record.price is not None]
    strict_blockers = [
        record
        for record in records
        if (record.core or record.required_for_operation)
        and (record.price is None or record.is_stale or record.quote_time is None)
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
    )


def records_to_dataframe(records: list[PriceRecord]) -> pd.DataFrame:
    return pd.DataFrame([record.output_dict() for record in records], columns=OUTPUT_COLUMNS)


def write_outputs(records: list[PriceRecord], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = records_to_dataframe(records)
    df.to_csv(output_dir / "prices_snapshot.csv", index=False, encoding="utf-8-sig")
    (output_dir / "data_completeness_report.md").write_text(build_completeness_report(records), encoding="utf-8")
    (output_dir / "energy_price_block.md").write_text(build_project_block(records, "energy", "能源账户价格事实块"), encoding="utf-8")
    (output_dir / "tech_price_block.md").write_text(build_project_block(records, "tech", "科技账户价格事实块"), encoding="utf-8")
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
        "## 如果为否，原因",
    ]
    lines.extend(_bullet_lines(summary.reasons))
    lines.extend(["", "## 缺失价格列表"])
    lines.extend(_record_lines(summary.missing_prices))
    lines.extend(["", "## stale 价格列表"])
    lines.extend(_record_lines(summary.stale_prices))
    lines.extend(["", "## quote_time 缺失列表"])
    lines.extend(_record_lines(summary.quote_time_missing, marker="quote_time_missing"))
    lines.extend(
        [
            "",
            "## 允许使用范围",
            "- 可用于价格事实同步、数据源核对、时间戳核对、市场状态核对和数据完整度检查。",
            "- 收盘后价格仅可作为收盘/最后成交参考。",
            "",
            "## 禁止使用范围",
            "- 不可用于自动交易。",
            "- 不输出买卖建议。",
            "- 若核心标的或 required_for_operation 指标缺失、stale 或 quote_time 缺失，不可用于具体操作建议。",
            "- 收盘/最后成交参考价不可用于盘中做T。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_project_block(records: list[PriceRecord], project: str, title: str) -> str:
    project_records = [record for record in records if record.project == project]
    lines = [
        f"# {title}",
        "",
        "仅为价格事实和新鲜度记录，不包含买卖建议。",
        "",
        "| symbol | name | price | currency | source | quote_time | fetch_time | market_status | is_stale | stale_reason |",
        "|---|---|---:|---|---|---|---|---|---|---|",
    ]
    for record in project_records:
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
    return "\n".join(lines) + "\n"


def build_controller_summary(records: list[PriceRecord]) -> str:
    project_names = {"energy": "能源账户", "tech": "科技账户", "controller": "总控辅助"}
    lines = [
        "# 总控价格摘要",
        "",
        "总控项目只维护摘要同步块，不输出能源/科技账户完整明细。",
        "",
        "| project | total | stale_or_missing | latest_fetch_time |",
        "|---|---:|---:|---|",
    ]
    for project in ["energy", "tech", "controller"]:
        project_records = [record for record in records if record.project == project]
        stale_count = sum(1 for record in project_records if record.is_stale or record.price is None)
        latest_fetch = max((record.fetch_time for record in project_records if record.fetch_time), default=None)
        lines.append(
            f"| {project_names[project]} | {len(project_records)} | {stale_count} | {latest_fetch.isoformat() if latest_fetch else ''} |"
        )

    lines.extend(["", "说明：若核心标的缺失或过期，相关项目不可用于具体操作建议。"])
    return "\n".join(lines) + "\n"


def _bullet_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- 无"]
    return [f"- {item}" for item in items]


def _record_lines(records: list[PriceRecord], marker: str | None = None) -> list[str]:
    if not records:
        return ["- 无"]
    prefix = f"{marker}: " if marker else ""
    return [
        f"- {prefix}{record.project} {record.symbol} {record.name}: {record.stale_reason}"
        for record in records
    ]
