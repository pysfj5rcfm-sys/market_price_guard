# HANDOFF v0.7.4

Version: `v0.7.4 | Account Layer Abstraction Foundation + Architecture Anchor`

This handoff is based on repository files, current scripts, current config, generated outputs, and validation commands from this thread. Do not rely on older chat history.

## 1. Scope Classification

scope classification: `account-generic foundation`

This version is not tech-only, not energy-only, and not controller-summary. It establishes account-generic foundations around layer config paths, config verification, and layer manager entry points while preserving the current tech behavior.

## 2. Completed Work

- Added `docs/ACCOUNT_ARCHITECTURE.md`.
- Added account path resolver in `src/market_price_guard/account_config.py`.
- Updated `src/market_price_guard/config_observability.py` so config checks can run by `account`.
- Added `src/market_price_guard/check_account_layer_config.py`.
- Added `scripts/check_account_layer_config.ps1`.
- Kept `scripts/check_tech_layer_config.ps1` as a tech compatibility wrapper.
- Added `src/market_price_guard/manage_account_layers.py`.
- Added `scripts/manage_account_layers.ps1`.
- Kept `scripts/manage_tech_layers.ps1` and `src/market_price_guard/manage_tech_layers.py` behavior compatible with v0.7.3.3.
- Added tests for account architecture, account path resolver, tech counts, energy not-bootstrapped behavior, and dry-run config safety.
- Updated runtime/UAT docs to state that market_price_guard is not tech-only.

## 3. ACCOUNT_ARCHITECTURE.md Summary

`docs/ACCOUNT_ARCHITECTURE.md` records:

- market_price_guard is not tech-only.
- Required execution accounts are `tech` and `energy`.
- Future `controller / portfolio summary` is summary-only and must not replace account execution.
- tech and energy must keep separate layer configs, operation pools, candidates, watchlists, scans, pipelines, outputs, UAT checks, handoffs, and account rules.
- Every future version must classify scope as `tech-only`, `energy-only`, `account-generic`, or `controller-summary`.
- Reusable infrastructure should default to account-generic.
- Every future handoff must include scope classification, account impact, tech status, energy status, controller status when relevant, tech-only debt, future energy adaptation cost, and next-thread read list.

## 4. Account-generic Config Check

New command:

```powershell
.\scripts\check_account_layer_config.ps1 -Account tech
.\scripts\check_account_layer_config.ps1 -Account energy
```

Tech output remains compatible:

- `outputs_config_check_latest/tech_layer_config_check.md`
- `outputs_config_check_latest/tech_layer_config_check.json`

Energy output is explicit and does not fallback to tech:

- `outputs_config_check_latest/energy_layer_config_check.md`
- `outputs_config_check_latest/energy_layer_config_check.json`
- status: `account_not_bootstrapped`
- exit code: `1` while energy is incomplete

Reports include account fields such as `account`, `scope_classification`, `account_project_path`, `root_mirror_path`, `account_bootstrapped`, `missing_account_config_files`, configured counts, loaded counts, root mirror match, warnings, and errors.

## 5. Account-generic Layer Manager

New command:

```powershell
.\scripts\manage_account_layers.ps1 -Account tech show
.\scripts\manage_account_layers.ps1 -Account tech validate
.\scripts\manage_account_layers.ps1 -Account tech export
.\scripts\manage_account_layers.ps1 -Account tech add 512480.SH -Layer watchlist -DryRun
.\scripts\manage_account_layers.ps1 -Account tech sync-root -DryRun
.\scripts\manage_account_layers.ps1 -Account energy show
.\scripts\manage_account_layers.ps1 -Account energy validate
```

Tech delegates to the v0.7.3.3 tech manager behavior and adds account metadata in the account-generic report. Energy currently reports `energy_account_not_bootstrapped`; it does not create energy files and does not read tech layer files.

## 6. Tech Wrapper Compatibility

Still works:

```powershell
.\scripts\check_tech_layer_config.ps1
.\scripts\manage_tech_layers.ps1 show
.\scripts\manage_tech_layers.ps1 validate
.\scripts\manage_tech_layers.ps1 export
```

The legacy tech manager still supports `show`, `validate`, `add`, `remove`, `move`, `sync-root`, `export`, and `backup` with the existing `-DryRun`, `-Backup`, `-ConfirmPolicyOverride`, and `-AllowOperationLayer` semantics.

## 7. Current Tech Status

Current tech layer counts:

| layer | count |
|---|---:|
| operation | 7 |
| operation_candidate | 11 |
| watchlist | 16 |
| scan | 30 |

Status:

- `manage_tech_layers.ps1` still works.
- `check_tech_layer_config.ps1` still works.
- `manage_account_layers.ps1 -Account tech show/validate/export` works.
- `check_account_layer_config.ps1 -Account tech` works.
- `git diff -- config` was clean after dry-run checks; this version did not automatically modify config.
- strict semantics unchanged.
- `usable_for_operation` semantics unchanged.
- `quote_trust_tier` semantics unchanged.
- No trading advice layer, action hint, or preferred action was added.

## 8. Current Energy Status

Energy is not bootstrapped yet.

Current repository has `config/universes/energy_core.yaml`, but account bootstrap is incomplete because these account layer files are missing:

- `config/universes/energy_operation_candidates.yaml`
- `config/universes/energy_watchlist.yaml`
- `config/universes/energy_scan.yaml`

Future root mirror path is reserved:

- `config/watchlist.yaml -> projects.energy.layer_universes`

No energy symbols were added by this version. No energy pipeline was created. No energy trading logic or energy trading advice was implemented.

## 9. Future Energy Config Paths

Reserved account path resolver mapping:

| layer | future path |
|---|---|
| operation | `config/universes/energy_core.yaml` |
| operation_candidate | `config/universes/energy_operation_candidates.yaml` |
| watchlist | `config/universes/energy_watchlist.yaml` |
| scan | `config/universes/energy_scan.yaml` |
| root mirror | `config/watchlist.yaml -> projects.energy.layer_universes` |

## 10. Remaining Tech-only Debt

Remaining tech-only scripts:

- `scripts/run_tech_research_pipeline.ps1`
- `scripts/run_tech_scan_ai.ps1`
- `scripts/run_tech_watchlist.ps1`
- `scripts/run_tech_operation_candidates.ps1`
- `scripts/run_tech_fast_strict.ps1`
- `scripts/run_tech_minute_probe.ps1`
- `scripts/run_tech_intraday_metrics.ps1`

Remaining tech-only implementation areas:

- Tech pipeline output directories are still `outputs_tech_*`.
- Pipeline summary and layer manifest aggregation are still tech-specific.
- UAT quick/intraday profiles still primarily validate tech execution paths.
- `market_price_guard.main` still has tech-specific manifest inference for current runtime paths.

## 11. Future Energy Adaptation Cost

Future energy adaptation requires:

- Bootstrap missing energy layer files.
- Add `projects.energy.layer_universes` root mirror.
- Define energy-specific account rules without inheriting tech strategy rules by default.
- Add account-aware pipeline runner or energy-specific pipeline wrapper that writes energy outputs separately.
- Add account-aware UAT items that keep tech and energy checks isolated.
- Extend layer manifest aggregation from tech pipeline to account-generic pipeline summaries.
- Decide whether controller summary reads account outputs only, without replacing account execution.

Estimated adaptation cost is moderate: path resolver and manager/checker foundations are now present, but pipeline, output, and UAT orchestration remain tech-only debt.

## 12. Account Impact

- tech: current behavior preserved; account-generic wrappers pass tech checks.
- energy: future paths reserved; incomplete bootstrap is reported clearly; no fallback to tech.
- controller: no behavior change; remains summary/reference scope only.

## 13. Next Version Suggestions

- `v0.7.3.5 | Energy Layer Pool Bootstrap`
- `v0.7.3.5 | Account Pipeline Abstraction Foundation`

Recommended order: bootstrap energy layer files and root mirror first if the next thread needs energy account execution pools; otherwise abstract pipeline/UAT before adding new energy runtime logic.

## 14. Acceptance Commands

```powershell
pytest -q
Test-Path docs\ACCOUNT_ARCHITECTURE.md
Get-Content docs\ACCOUNT_ARCHITECTURE.md -Encoding UTF8
.\scripts\check_account_layer_config.ps1 -Account tech
Get-Content outputs_config_check_latest\tech_layer_config_check.md -Encoding UTF8
.\scripts\check_tech_layer_config.ps1
.\scripts\manage_account_layers.ps1 -Account tech show
.\scripts\manage_account_layers.ps1 -Account tech validate
.\scripts\manage_account_layers.ps1 -Account tech export
.\scripts\manage_tech_layers.ps1 show
.\scripts\manage_tech_layers.ps1 validate
.\scripts\manage_tech_layers.ps1 export
.\scripts\manage_account_layers.ps1 -Account energy show
.\scripts\manage_account_layers.ps1 -Account energy validate
.\scripts\check_account_layer_config.ps1 -Account energy
.\scripts\manage_account_layers.ps1 -Account tech add 512480.SH -Layer watchlist -DryRun
git diff -- config
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
Select-String -Path outputs_config_manager_latest\*.md,outputs_config_check_latest\*.md,outputs_tech_pipeline_latest\*.md -Pattern "买入|卖出|加仓|减仓|做T|挂单|目标价|入场价|止损|preferred_action|action_hint|buy|sell|add|reduce" -CaseSensitive:$false
```

Validation from this thread:

- `pytest -q`: `328 passed`.
- `check_account_layer_config.ps1 -Account tech`: exit `0`.
- `check_tech_layer_config.ps1`: exit `0`.
- `manage_account_layers.ps1 -Account tech show/validate/export`: exit `0`.
- `manage_tech_layers.ps1 show/validate/export`: exit `0`.
- `manage_account_layers.ps1 -Account energy show`: reports not bootstrapped; exit `1`.
- `manage_account_layers.ps1 -Account energy validate`: reports missing energy files; exit `1`.
- `check_account_layer_config.ps1 -Account energy`: reports not bootstrapped; exit `1`.
- `manage_account_layers.ps1 -Account tech add 512480.SH -Layer watchlist -DryRun`: exit `0`; no config diff.
- `run_tech_research_pipeline.ps1 -UseRunCache`: exit `0`.
- `run_uat.ps1 -Mode quick -UseRunCache`: exit `0`.
- `run_uat.ps1 -Mode intraday -UseRunCache`: exit `0`.
- No-advice keyword scan over requested Markdown outputs: no matches after report display sanitization.

## 15. Strictly Out Of Scope

- No QDII premium.
- No NDX / QQQ / FX reference work.
- No advice layer.
- No `action_hint`.
- No `preferred_action`.
- No buy/sell/add/reduce/do-T/order-price/target-price outputs.
- No automatic scan to watchlist writes.
- No automatic watchlist to operation-candidate writes.
- No automatic operation-candidate to operation promotion.
- No strict semantics change.
- No `usable_for_operation` semantics change.
- No `quote_trust_tier` semantics change.
- No provider priority change.
- No YFinance circuit change.
- No AKShare / Eastmoney / YFinance main flow change.
- No provider runtime hardening.
- No position, cost, gold amount, or controller 1,000,000 CNY denominator change.
- No tech symbols added to energy config.
- No energy symbols added to tech config.
- No tech strategy rules applied to energy by default.
- No full energy pipeline.
- No energy trading advice.
- No UI.

## 16. Known Issues

- `config/universes/energy_core.yaml` exists, but energy is still incomplete until the other three layer files and root mirror are created.
- Account-generic manager delegates tech behavior to the existing tech manager rather than fully replacing internals.
- Pipeline and UAT remain mostly tech-specific.
- Live pipeline can still be slow; the first pipeline attempt timed out at 5 minutes, while the rerun completed in about 7 minutes.
- Console output may still include raw internal policy marker names; Markdown reports sanitize mechanical no-advice scan collisions.

## 17. Next Thread Should Read First

- `docs/ACCOUNT_ARCHITECTURE.md`
- `docs/HANDOFF_v0.7.4.md`
- `docs/HANDOFF_v0.7.3.3.md`
- `scripts/manage_account_layers.ps1`
- `scripts/check_account_layer_config.ps1`
- `scripts/manage_tech_layers.ps1`
- `scripts/check_tech_layer_config.ps1`
- `config/watchlist.yaml`
- `config/universes/tech_core.yaml`
- `config/universes/tech_operation_candidates.yaml`
- `config/universes/tech_watchlist.yaml`
- `config/universes/tech_scan_ai.yaml`
