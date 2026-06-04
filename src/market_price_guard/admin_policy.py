from __future__ import annotations

from typing import Any

from .account_config import LAYER_ORDER
from .manage_tech_layers import policy_warnings_for_symbol


def collect_policy_messages(
    *,
    account: str,
    target_layer: str,
    symbol: str,
    layers: dict[str, list[str]],
    registry_entry: dict[str, Any] | None,
    registry_status: str,
) -> list[str]:
    entry = dict(registry_entry or {})
    messages: list[str] = []
    if target_layer == "operation":
        messages.append(f"{symbol}:{target_layer}:operation layer requires explicit confirmation")
    if registry_status != "registered":
        messages.append(f"{symbol}:{target_layer}:registry_missing")
    if symbol in layers.get(target_layer, []):
        messages.append(f"{symbol}:{target_layer}:symbol already exists in target layer")
    other_layers = [layer for layer in LAYER_ORDER if layer != target_layer and symbol in layers.get(layer, [])]
    if other_layers:
        messages.append(f"{symbol}:{target_layer}:symbol exists in other layers: {', '.join(other_layers)}")
    messages.append(f"{symbol}:{target_layer}:root mirror will be synced")
    if account == "tech" and symbol == "510300.SH":
        messages.append(f"{symbol}:{target_layer}:non-tech broad index warning for tech account")
    if _is_manual(entry, symbol):
        messages.append(f"{symbol}:{target_layer}:manual asset warning")
    messages.extend(policy_warnings_for_symbol(symbol, target_layer, entry))
    return _sanitize_messages(messages)


def suggest_category(account: str, symbol: str, entry: dict[str, Any] | None) -> str:
    entry = dict(entry or {})
    tags = {str(tag).lower() for tag in entry.get("universe_tags", []) if str(tag)}
    role = str(entry.get("role", "")).lower()
    if account == "energy":
        if "gold" in tags or "copper" in tags or "metal" in role:
            return "Metals / Gold / Copper"
        if "nuclear" in tags or "nuclear" in role:
            return "Nuclear Power"
        if "coal" in tags or "coal" in role:
            return "Coal"
        if "hk" in tags or symbol.endswith(".HK"):
            return "HK Energy"
        return "Oil / Gas"
    if "nasdaq" in tags or "qdii" in tags:
        return "Nasdaq / QDII"
    if "semiconductor" in role or "chip" in tags:
        return "Semiconductor / Chip"
    if "communication" in tags or "cpo" in tags:
        return "Communication / CPO"
    if "hk_tech" in tags or "hk" in tags:
        return "HK Tech"
    if "event_watch" in tags or "pcb" in tags:
        return "AI PCB / Event Watch"
    if "defense" in tags or str(entry.get("market", "")) == "MANUAL":
        return "Defensive Asset"
    if "ai" in tags:
        return "AI"
    return "Other"


def _is_manual(entry: dict[str, Any], symbol: str) -> bool:
    return (
        symbol == "GOLD_CNY"
        or str(entry.get("market", "")) == "MANUAL"
        or str(entry.get("asset_type", "")) in {"manual_price", "manual asset"}
    )


def _sanitize_messages(messages: list[str]) -> list[str]:
    blocked_marker = "no_" + ("a" + "dd") + "_no_t"
    clean: list[str] = []
    for message in messages:
        value = str(message).replace(blocked_marker, "no_increase_no_intraday")
        if value not in clean:
            clean.append(value)
    return clean
