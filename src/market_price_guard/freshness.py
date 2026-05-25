from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any

from .models import RawPrice


SHANGHAI_TZ = timezone(timedelta(hours=8))
HONG_KONG_TZ = timezone(timedelta(hours=8))
FUTURE_QUOTE_TOLERANCE_SECONDS = 120


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def assess_freshness(raw: RawPrice, market: str, rules: dict[str, Any], now: datetime | None = None) -> tuple[bool, str]:
    current_time = _to_utc(now or now_utc())
    market_status = market_status_for_now(raw, market, current_time)

    if raw.quality_issues:
        issue_text = ", ".join(raw.quality_issues)
        if "akshare_not_installed" in raw.quality_issues:
            return True, f"akshare_not_installed: AKShare 未安装，不可用于具体操作建议；{issue_text}"
        if "provider_error" in raw.quality_issues:
            return True, f"provider_error: 行情源调用失败，不可用于具体操作建议；{issue_text}"
        if "provider_timeout" in raw.quality_issues:
            return True, f"provider_timeout: 行情源调用超过单次预算且未返回可用结果，不可用于具体操作建议；{issue_text}"
        if "symbol_not_found" in raw.quality_issues:
            return True, f"symbol_not_found: 行情源未返回该标的，不可用于具体操作建议；{issue_text}"
        if "invalid_price" in raw.quality_issues:
            return True, f"invalid_price: 价格缺失或不是正数，不可用于具体操作建议；{issue_text}"
        if "invalid_quote_time" in raw.quality_issues:
            return True, f"invalid_quote_time: quote_time 解析失败，不可用于具体操作建议；{issue_text}"
        if "quote_time_missing" in raw.quality_issues:
            return True, f"quote_time_missing: quote_time 缺失，无法证明价格新鲜，不可用于具体操作建议；{issue_text}"
        if "mock_fallback_not_allowed" in raw.quality_issues:
            return True, f"mock_fallback_not_allowed: mock fallback 不可用于具体操作建议；{issue_text}"
        if "manual_fallback_not_allowed" in raw.quality_issues:
            return True, f"manual_fallback_not_allowed: manual fallback 未配置为可用于具体操作建议；{issue_text}"

    if raw.price is None:
        return True, "价格缺失，不可用于具体操作建议"
    if raw.quote_time is None:
        return True, "quote_time_missing: quote_time 缺失，数据质量不足，不可用于具体操作建议"

    reference_time = raw.entry_time if raw.source == "manual" and raw.entry_time else raw.quote_time
    age_seconds = (_to_utc(current_time) - _to_utc(reference_time)).total_seconds()

    if age_seconds < 0:
        if abs(age_seconds) <= FUTURE_QUOTE_TOLERANCE_SECONDS:
            age_seconds = 0
        else:
            return True, f"future_quote_time: 时间戳晚于当前时间且超过 {FUTURE_QUOTE_TOLERANCE_SECONDS} 秒容忍，数据质量不足"

    if raw.source == "manual" or market == "MANUAL":
        manual_rules = rules.get("MANUAL", rules.get("manual", {}))
        max_age = int(manual_rules.get("max_age_seconds", 0))
        if age_seconds > max_age:
            return True, "manual 价格超过允许录入时间（MANUAL max_age_seconds），不可用于具体操作建议"
        return False, "manual 价格，已显示录入时间"

    market_rules = rules.get("markets", {}).get(market, rules.get("default", {}))
    if market_status == "open":
        max_age = int(market_rules.get("max_age_seconds_open", rules.get("default", {}).get("max_age_seconds_open", 0)))
        if age_seconds > max_age:
            return True, "交易中价格超过 max_age_seconds，不可用于具体操作建议"
        return False, "交易中价格在新鲜度阈值内"

    if market_status == "closed":
        max_age = int(market_rules.get("max_age_seconds_closed", rules.get("default", {}).get("max_age_seconds_closed", 0)))
        if not bool(market_rules.get("closed_market_allowed", rules.get("default", {}).get("closed_market_allowed", True))):
            return True, "closed_market_not_allowed: 市场已收盘，配置不允许使用收盘后参考价，不可用于具体操作建议"
        if age_seconds > max_age:
            return True, "收盘参考价超过允许时间，不可用于具体操作建议"
        return False, "市场已收盘；价格为收盘前/最后更新时间参考，不适合盘中做T判断"

    return True, "market_status 未知，数据质量不足，不可用于具体操作建议"


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def market_status_for_now(raw: RawPrice, market: str, now: datetime) -> str:
    if raw.market_status == "manual" or raw.source == "manual" or market == "MANUAL":
        return raw.market_status
    if raw.source == "mock" and raw.market_status in {"open", "closed"}:
        return raw.market_status
    if market == "CN" and raw.symbol.endswith((".SH", ".SZ")):
        current = _to_utc(now).astimezone(SHANGHAI_TZ).time()
        return "open" if _in_ranges(current, [(time(9, 30), time(11, 30)), (time(13, 0), time(15, 0))]) else "closed"
    if market == "HK" and raw.symbol.endswith(".HK"):
        current = _to_utc(now).astimezone(HONG_KONG_TZ).time()
        return "open" if _in_ranges(current, [(time(9, 30), time(12, 0)), (time(13, 0), time(16, 0))]) else "closed"
    return raw.market_status


def _in_ranges(value: time, ranges: list[tuple[time, time]]) -> bool:
    return any(start <= value < end for start, end in ranges)
