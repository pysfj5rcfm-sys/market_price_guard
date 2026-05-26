# HANDOFF v0.7.4.1

Version: `v0.7.4.1 | Energy Layer Pool Bootstrap`

This handoff is based on repository files, current scripts, current config, generated outputs, and validation commands from this thread. Do not rely on older chat history.

## 1. Scope Classification

scope classification: `energy-only bootstrap using account-generic infrastructure`

This version is energy-only bootstrap work. It is not tech-only, not controller-summary, not provider runtime hardening, and not an energy research pipeline.

## 2. Completed Work

- Created `config/universes/energy_operation_candidates.yaml`.
- Created `config/universes/energy_watchlist.yaml`.
- Created `config/universes/energy_scan.yaml`.
- Kept `config/universes/energy_core.yaml` as the authority for the initial operation layer.
- Added `projects.energy.layer_universes` and `projects.energy.layer_counts` to `config/watchlist.yaml`.
- Extended account-generic manager behavior so bootstrapped non-tech accounts can `show`, `validate`, `export`, `sync-root`, `backup`, `add`, `remove`, and `move`.
- Kept tech account behavior delegated to the existing tech manager.
- Updated config check reports with `root_mirror_match`, `missing_config_files`, and `registry_missing_symbols` aliases.
- Added/updated tests for energy bootstrap files, root mirror, registry coverage, no fallback to tech, energy manager commands, and unchanged tech counts.

## 3. Current Energy Layer State

| layer | file | count |
|---|---|---:|
| operation | `config/universes/energy_core.yaml` | 4 |
| operation_candidate | `config/universes/energy_operation_candidates.yaml` | 0 |
| watchlist | `config/universes/energy_watchlist.yaml` | 4 |
| scan | `config/universes/energy_scan.yaml` | 4 |

Energy symbols:

- `00883.HK`
- `601899.SH`
- `601985.SH`
- `003816.SZ`

`energy_operation_candidates.yaml` is intentionally empty. `energy_watchlist.yaml` and `energy_scan.yaml` mirror operation symbols only for bootstrap.

## 4. Energy Root Mirror

`config/watchlist.yaml -> projects.energy.layer_universes` now mirrors the four energy universe files:

- operation: matches `energy_core.yaml`
- operation_candidate: matches `energy_operation_candidates.yaml`
- watchlist: matches `energy_watchlist.yaml`
- scan: matches `energy_scan.yaml`

Current check report status:

- account: `energy`
- account_bootstrapped: `true`
- root_mirror_match: `true`
- missing_config_files: `[]`
- registry_missing_symbols: `[]`

## 5. Tech Status

Tech layer counts remain unchanged:

| layer | count |
|---|---:|
| operation | 7 |
| operation_candidate | 11 |
| watchlist | 16 |
| scan | 30 |

Tech wrappers still pass:

- `scripts/check_tech_layer_config.ps1`
- `scripts/manage_tech_layers.ps1 show`
- `scripts/manage_tech_layers.ps1 validate`
- `scripts/manage_tech_layers.ps1 export`

No tech config symbols were changed by this version.

## 6. Explicit Non-Goals

- No energy pipeline was implemented.
- No energy UAT profile was implemented.
- No energy trading logic was implemented.
- No provider priority was changed.
- No strict semantics were changed.
- No `usable_for_operation` semantics were changed.
- No `quote_trust_tier` semantics were changed.
- No positions, costs, gold amount, or controller 1,000,000 CNY denominator were changed.
- No tech symbols were added to energy config.
- No energy symbols were added to tech config.

## 7. Validation Results

- `pytest`: `329 passed`.
- `.\scripts\check_account_layer_config.ps1 -Account energy`: exit `0`.
- `.\scripts\manage_account_layers.ps1 -Account energy show`: exit `0`.
- `.\scripts\manage_account_layers.ps1 -Account energy validate`: exit `0`.
- `.\scripts\manage_account_layers.ps1 -Account energy export`: exit `0`.
- `.\scripts\manage_account_layers.ps1 -Account energy sync-root -DryRun`: exit `0`.
- `.\scripts\check_account_layer_config.ps1 -Account tech`: exit `0`.
- `.\scripts\check_tech_layer_config.ps1`: exit `0`.
- `.\scripts\manage_account_layers.ps1 -Account tech show/validate/export`: exit `0`.
- `.\scripts\manage_tech_layers.ps1 show/validate/export`: exit `0`.
- `.\scripts\run_tech_research_pipeline.ps1 -UseRunCache`: exit `0`.
- `.\scripts\run_uat.ps1 -Mode quick -UseRunCache`: exit `0`.
- `.\scripts\run_uat.ps1 -Mode intraday -UseRunCache`: exit `0`.
- No-advice keyword scan over requested Markdown outputs: no matches.

UAT note: `mock_strict` can remain `strict_blocked_but_reported` inside the UAT summary when stale mock quotes are intentionally blocked and reports are generated. The quick and intraday UAT scripts exited `0`.

## 8. Generated Reports

- `outputs_config_check_latest/energy_layer_config_check.md`
- `outputs_config_check_latest/energy_layer_config_check.json`
- `outputs_config_manager_latest/energy_layer_config_export.md`
- `outputs_config_manager_latest/energy_layer_config_export.json`
- `outputs_config_manager_latest/energy_layer_config_export.csv`

## 9. Strictly Forbidden For This Version

- No QDII premium.
- No NDX / QQQ / FX reference work.
- No advice layer.
- No `action_hint`.
- No `preferred_action`.
- No trading instruction outputs.
- No automatic scan to watchlist writes.
- No automatic watchlist to operation-candidate writes.
- No automatic operation-candidate to operation promotion.
- No provider runtime hardening.
- No full energy pipeline.
- No energy trading advice.
- No UI.

## 10. Next Version Suggestion

Recommended next version:

`v0.7.4.2 | Energy Layer Pool Expansion / Energy Research Pipeline Bootstrap`

Suggested order:

1. Let the user confirm any expanded energy candidate/watchlist/scan universe.
2. Add account-aware energy research pipeline bootstrap only after layer pool expansion is agreed.
3. Keep tech and energy outputs, UAT, and handoffs separate.

## 11. Acceptance Commands

```powershell
pytest
.\scripts\check_account_layer_config.ps1 -Account energy
Get-Content outputs_config_check_latest\energy_layer_config_check.md -Encoding UTF8
.\scripts\manage_account_layers.ps1 -Account energy show
.\scripts\manage_account_layers.ps1 -Account energy validate
.\scripts\manage_account_layers.ps1 -Account energy export
.\scripts\manage_account_layers.ps1 -Account energy sync-root -DryRun
.\scripts\check_account_layer_config.ps1 -Account tech
.\scripts\check_tech_layer_config.ps1
.\scripts\manage_account_layers.ps1 -Account tech show
.\scripts\manage_account_layers.ps1 -Account tech validate
.\scripts\manage_account_layers.ps1 -Account tech export
.\scripts\manage_tech_layers.ps1 show
.\scripts\manage_tech_layers.ps1 validate
.\scripts\manage_tech_layers.ps1 export
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
Select-String -Path `
  outputs_config_manager_latest\*.md,`
  outputs_config_check_latest\*.md,`
  outputs_tech_pipeline_latest\*.md `
  -Pattern "买入|卖出|加仓|减仓|做T|挂单|目标价|入场价|止损|preferred_action|action_hint|buy|sell|add|reduce" `
  -CaseSensitive:$false
```

## 12. Next Thread Should Read First

- `docs/ACCOUNT_ARCHITECTURE.md`
- `docs/HANDOFF_v0.7.4.1.md`
- `docs/HANDOFF_v0.7.4.md`
- `scripts/manage_account_layers.ps1`
- `scripts/check_account_layer_config.ps1`
- `config/watchlist.yaml`
- `config/universes/energy_core.yaml`
- `config/universes/energy_operation_candidates.yaml`
- `config/universes/energy_watchlist.yaml`
- `config/universes/energy_scan.yaml`
- `config/symbol_registry.yaml`
