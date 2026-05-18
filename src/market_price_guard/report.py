from __future__ import annotations

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
    core_problem_records = [record for record in records if record.core and (record.price is None or record.is_stale)]
    status = "不可用于具体操作建议" if core_problem_records else "数据完整度通过"
    lines = [
        "# 数据完整度报告",
        "",
        f"结论：{status}",
        "",
        "本工具不做自动交易，不输出买卖建议，只输出价格事实、数据源、时间戳、市场状态和数据完整度。",
        "",
        "## 异常核心标的",
    ]
    if core_problem_records:
        for record in core_problem_records:
            lines.append(f"- {record.project} {record.symbol} {record.name}: {record.stale_reason}")
    else:
        lines.append("- 无")
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
