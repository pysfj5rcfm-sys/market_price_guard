from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _git_diff(*paths: str) -> str:
    result = subprocess.run(["git", "diff", "--", *paths], check=True, capture_output=True, text=True)
    return result.stdout


def test_admin_version_does_not_change_provider_router_or_config():
    assert _git_diff("src/market_price_guard/provider_router.py") == ""
    assert _git_diff("config") == ""


def test_admin_version_does_not_change_strict_or_usable_runtime_files():
    assert _git_diff(
        "src/market_price_guard/provider_router.py",
        "src/market_price_guard/main.py",
        "src/market_price_guard/report.py",
    ) == ""


def test_admin_no_trading_advice_keywords_in_new_ui_surfaces():
    pattern = re.compile(
        r"买入|卖出|加仓|减仓|做T|挂单|目标价|入场价|止损|preferred_action|action_hint|buy|sell|add|reduce",
        re.IGNORECASE,
    )
    paths = list(Path("src/market_price_guard").glob("admin*.py"))
    paths.extend(Path("templates/admin").glob("*.html"))
    handoff = Path("docs/HANDOFF_v0.8.0.md")
    if handoff.exists():
        paths.append(handoff)

    hits: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            hits.append(f"{path}:{match.group(0)}")

    assert hits == []
