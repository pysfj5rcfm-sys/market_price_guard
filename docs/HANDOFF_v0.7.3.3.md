# HANDOFF v0.7.3.3

Version: `v0.7.3.3 | Tech Layer Config Manager CLI`

This handoff is based on repository files, current scripts, current config, and validation commands from this thread. Do not rely on older chat history.

## 1. Completed Work

- Added `scripts/manage_tech_layers.ps1`.
- Added `src/market_price_guard/manage_tech_layers.py`.
- Added tests in `tests/test_manage_tech_layers.py`.
- Updated `src/market_price_guard/config_observability.py` so specific symbols such as `002463.SZ`, `159516.SZ`, `510300.SH`, and `GOLD_CNY` are policy warnings, not permanent structural hard blocks.
- Kept provider behavior, strict semantics, `usable_for_operation`, `quote_trust_tier`, provider priority, positions, costs, gold amount, and total-control account scope unchanged.

## 2. CLI Usage

```powershell
.\scripts\manage_tech_layers.ps1 show
.\scripts\manage_tech_layers.ps1 validate
.\scripts\manage_tech_layers.ps1 add 512480.SH -Layer watchlist -DryRun
.\scripts\manage_tech_layers.ps1 remove 513180.SH -Layer watchlist -DryRun
.\scripts\manage_tech_layers.ps1 move 159558.SZ -From operation_candidate -To watchlist -DryRun
.\scripts\manage_tech_layers.ps1 sync-root -DryRun
.\scripts\manage_tech_layers.ps1 export
.\scripts\manage_tech_layers.ps1 backup
```

Supported layer names:

- `operation`
- `operation_candidate`
- `watchlist`
- `scan`

Supported aliases:

- `core`, `tech_core` -> `operation`
- `candidate`, `operation_candidates`, `tech_operation_candidates` -> `operation_candidate`
- `tech_watchlist` -> `watchlist`
- `tech_scan_ai` -> `scan`

## 3. Commands

- `show`: prints four layer counts/symbols and root mirror status. It does not modify config.
- `validate`: runs the config check logic and writes `outputs_config_check_latest`.
- `add`: adds one registered symbol to one layer, syncs root mirror, and validates after actual writes.
- `remove`: removes one symbol from one layer, syncs root mirror, and validates after actual writes.
- `move`: removes from one layer and adds to another layer, syncs root mirror, and validates after actual writes.
- `sync-root`: treats `config/universes/*.yaml` as authoritative and rebuilds `config/watchlist.yaml -> projects.tech.layer_universes`.
- `export`: writes `outputs_config_manager_latest/tech_layer_config_export.md`, `.json`, and `.csv`.
- `backup`: copies current layer config files to `backups/config_layers_YYYYMMDD_HHMMSS/`.

## 4. Structural Hard Rules

- Layer names must normalize to one of the four supported layers.
- Symbol format must be valid.
- Symbols must exist in `config/symbol_registry.yaml` by default.
- Duplicate symbols inside one top-level `symbols` list are structural errors.
- `-DryRun` does not write config files.
- `-Backup` creates a backup before actual writes.
- Root layer mirror is synchronized from universe files after actual `add`, `remove`, `move`, and `sync-root`.
- Operation layer modification requires `-AllowOperationLayer`.
- The CLI does not alter positions, costs, gold amount, total-control account scope, provider behavior, strict, `usable_for_operation`, or `quote_trust_tier`.

## 5. Policy Warnings

Policy warning tags are reported but are not permanent hard blocks:

- `failed_trial_observation`
- `failed_trial_observation_only`
- `no_add_no_t`
- `not_repair_candidate`
- `new_trade_requires_full_re_evaluation`
- `event_stock`
- `event_watch_only`
- `individual_stock`
- `manual_price_only`
- `defensive_asset`
- `broad_base_reference`
- `non_tech_asset`
- `qdii_premium_required`
- `premium_required`
- `non_default_candidate`
- `operation_validator`
- `reference_only`

Special current behavior:

- `159516.SZ` in `operation_candidate` reports failed-trial observation and restriction warnings.
- `002463.SZ` in `operation_candidate` reports event-stock candidate warnings and event-state review warnings.
- `510300.SH` in `operation_candidate` reports non-tech candidate warning.
- `GOLD_CNY` in `operation_candidate` reports manual-price warning.
- QDII premium markers report that premium data is required before any operation decision.

## 6. Override Mechanism

If an actual modifying command would change config for a symbol with relevant policy warnings, the CLI requires:

```powershell
-ConfirmPolicyOverride
```

When used, the report records:

- `policy_override_used=true`
- `override_scope=<symbol/layer>`
- `override_reason=user_explicit_command`

Dry runs show whether an override would be required but do not write files.

## 7. Dry Run / Backup / Sync Root

- `-DryRun` prints changed files, before/after counts, symbol diffs, structural status, policy warnings, and root mirror sync intent without writing config.
- `-Backup` creates `backups/config_layers_YYYYMMDD_HHMMSS/` before actual writes.
- `sync-root` only rebuilds `projects.tech.layer_universes` and `layer_counts` from universe files. It does not broaden `projects.tech.instruments`.

## 8. Current Counts

Current target counts:

| layer | count |
|---|---:|
| operation | 7 |
| operation_candidate | 11 |
| watchlist | 16 |
| scan | 30 |

Root mirror currently matches all four universe files.

## 9. New Files

- `scripts/manage_tech_layers.ps1`
- `src/market_price_guard/manage_tech_layers.py`
- `tests/test_manage_tech_layers.py`
- `docs/HANDOFF_v0.7.3.3.md`

Updated:

- `src/market_price_guard/config_observability.py`

## 10. Known Issues

- YAML writes use PyYAML and may rewrite formatting/comments in the touched config files.
- Nested grouping metadata under universe files is not automatically reclassified; the authoritative top-level `symbols` list and root mirror are synchronized.
- The local `.venv` Python may be inaccessible inside the Codex sandbox. The new manager script falls back to bundled/runtime Python plus `.venv` site-packages for this environment.
- Existing live provider runtime issues remain unchanged.

## 11. Next Version Suggestions

- Optional registry-managed symbol add flow.
- Optional nested group maintenance for `layers.*.symbols` if a stable grouping policy is defined.
- Optional machine-readable schema for config manager reports.
- Optional narrower policy warning scopes for validate reports.

## 12. Acceptance Commands

```powershell
pytest
.\scripts\manage_tech_layers.ps1 show
.\scripts\manage_tech_layers.ps1 validate
Get-Content outputs_config_check_latest\tech_layer_config_check.md -Encoding UTF8
.\scripts\manage_tech_layers.ps1 export
Get-Content outputs_config_manager_latest\config_manager_report.md -Encoding UTF8
.\scripts\manage_tech_layers.ps1 add 512480.SH -Layer watchlist -DryRun
.\scripts\manage_tech_layers.ps1 remove 512480.SH -Layer watchlist -DryRun
.\scripts\manage_tech_layers.ps1 add 002463.SZ -Layer operation_candidate -DryRun
.\scripts\manage_tech_layers.ps1 add 002463.SZ -Layer operation_candidate -DryRun -ConfirmPolicyOverride
.\scripts\manage_tech_layers.ps1 add 512480.SH -Layer operation -DryRun
.\scripts\manage_tech_layers.ps1 add 512480.SH -Layer operation -DryRun -AllowOperationLayer
.\scripts\manage_tech_layers.ps1 backup
.\scripts\manage_tech_layers.ps1 sync-root -DryRun
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
```

## 13. Strictly Out Of Scope

- Do not implement QDII premium.
- Do not implement NDX / QQQ / FX reference.
- Do not implement advice layer, `action_hint`, or `preferred_action`.
- Do not output trading instructions, execution prices, or target prices.
- Do not auto-promote scan/watchlist/candidate symbols.
- Do not change provider priority, YFinance circuit behavior, AKShare/Eastmoney/YFinance flow, strict, `usable_for_operation`, or `quote_trust_tier`.
- Do not modify positions, costs, gold amount, or total-control account scope.
- Do not add UI.

## 14. Next Thread Should Read First

- `docs/HANDOFF_v0.7.3.3.md`
- `docs/HANDOFF_v0.7.3.2.md`
- `scripts/manage_tech_layers.ps1`
- `scripts/check_tech_layer_config.ps1`
- `config/watchlist.yaml`
- `config/universes/tech_core.yaml`
- `config/universes/tech_operation_candidates.yaml`
- `config/universes/tech_watchlist.yaml`
- `config/universes/tech_scan_ai.yaml`
