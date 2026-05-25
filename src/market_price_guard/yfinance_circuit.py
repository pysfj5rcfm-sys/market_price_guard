from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


RATE_LIMIT_MARKERS = ("Too Many Requests", "Rate limited", "YFRateLimitError")


@dataclass
class YFinanceCircuitBreaker:
    attempted_count: int = 0
    success_count: int = 0
    error_count: int = 0
    timeout_count: int = 0
    consecutive_timeout_count: int = 0
    rate_limited_count: int = 0
    skipped_by_circuit_count: int = 0
    base_quote_skipped_by_circuit_count: int = 0
    minute_skipped_by_circuit_count: int = 0
    total_elapsed_seconds: float = 0.0
    open: bool = False
    reason: str = ""
    opened_at: str = ""
    last_error: str = ""

    def allow(self) -> bool:
        return not self.open

    def record_success(self, elapsed_seconds: float = 0.0) -> None:
        self.attempted_count += 1
        self.success_count += 1
        self.total_elapsed_seconds += float(elapsed_seconds or 0.0)
        self.consecutive_timeout_count = 0

    def record_error(self, message: str = "", elapsed_seconds: float = 0.0, timeout: bool = False, symbol: str = "") -> None:
        self.attempted_count += 1
        self.error_count += 1
        self.total_elapsed_seconds += float(elapsed_seconds or 0.0)
        self.last_error = _short_text(message)
        if _is_rate_limited(message):
            self.rate_limited_count += 1
            self._open("rate_limited", symbol)
            return
        if timeout:
            self.timeout_count += 1
            self.consecutive_timeout_count += 1
            if self.consecutive_timeout_count >= 2 or self.timeout_count >= 3:
                self._open("repeated_timeout", symbol)
                return
        else:
            self.consecutive_timeout_count = 0
        if self.error_count >= 3:
            self._open("repeated_error", symbol)

    def record_timeout(self, message: str = "", elapsed_seconds: float = 0.0, symbol: str = "") -> None:
        self.record_error(message or "provider_timeout", elapsed_seconds=elapsed_seconds, timeout=True, symbol=symbol)

    def record_skip(self, scope: str = "") -> None:
        self.skipped_by_circuit_count += 1
        if scope == "base_quote":
            self.base_quote_skipped_by_circuit_count += 1
        elif scope == "minute":
            self.minute_skipped_by_circuit_count += 1

    def snapshot(self) -> dict[str, object]:
        return {
            "yfinance_circuit_open": self.open,
            "yfinance_circuit_reason": self.reason,
            "yfinance_circuit_opened_at": self.opened_at,
            "yfinance_circuit_scope": "run_only",
            "yfinance_total_elapsed_seconds": round(self.total_elapsed_seconds, 3),
            "yfinance_attempted_count": self.attempted_count,
            "yfinance_success_count": self.success_count,
            "yfinance_error_count": self.error_count,
            "yfinance_timeout_count": self.timeout_count,
            "yfinance_rate_limited_count": self.rate_limited_count,
            "yfinance_skipped_by_circuit_count": self.skipped_by_circuit_count,
            "fallback_skipped_yfinance_circuit_open_count": self.skipped_by_circuit_count,
            "base_quote_yfinance_skipped_by_circuit_count": self.base_quote_skipped_by_circuit_count,
            "minute_yfinance_skipped_by_circuit_count": self.minute_skipped_by_circuit_count,
            "yfinance_last_error": self.last_error,
        }

    def _open(self, reason: str, symbol: str = "") -> None:
        if self.open:
            return
        self.open = True
        self.reason = reason
        marker = symbol or datetime.now(timezone.utc).isoformat()
        self.opened_at = marker


def _is_rate_limited(message: str) -> bool:
    return any(marker.lower() in str(message).lower() for marker in RATE_LIMIT_MARKERS)


def _short_text(text: str, limit: int = 160) -> str:
    return str(text).replace("\n", " ").replace("\r", " ").replace(";", ",")[:limit]
