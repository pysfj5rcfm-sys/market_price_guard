from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import RawPrice


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def assess_freshness(raw: RawPrice, market: str, rules: dict[str, Any], now: datetime | None = None) -> tuple[bool, str]:
    current_time = now or now_utc()

    if raw.price is None:
        return True, "价格缺失，不可用于具体操作建议"
    if raw.quote_time is None:
        return True, "quote_time 缺失，数据质量不足，不可用于具体操作建议"

    reference_time = raw.entry_time if raw.source == "manual" and raw.entry_time else raw.quote_time
    age_seconds = (current_time - reference_time).total_seconds()

    if age_seconds < 0:
        return True, "时间戳晚于当前时间，数据质量不足"

    if raw.source == "manual":
        max_age = int(rules.get("manual", {}).get("max_age_seconds", 0))
        if age_seconds > max_age:
            return True, "manual 价格超过允许录入时间，不可用于具体操作建议"
        return False, "manual 价格，已显示录入时间"

    market_rules = rules.get("markets", {}).get(market, rules.get("default", {}))
    if raw.market_status == "open":
        max_age = int(market_rules.get("max_age_seconds_open", rules.get("default", {}).get("max_age_seconds_open", 0)))
        if age_seconds > max_age:
            return True, "交易中价格超过 max_age_seconds，不可用于具体操作建议"
        return False, "交易中价格在新鲜度阈值内"

    if raw.market_status == "closed":
        max_age = int(market_rules.get("max_age_seconds_closed", rules.get("default", {}).get("max_age_seconds_closed", 0)))
        if age_seconds > max_age:
            return True, "收盘参考价超过允许时间，不可用于具体操作建议"
        return False, "收盘/最后成交参考价，不可用于盘中做T"

    return True, "market_status 未知，数据质量不足，不可用于具体操作建议"
