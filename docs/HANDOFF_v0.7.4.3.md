# HANDOFF v0.7.4.3

Version: `v0.7.4.3 | Energy Research Pipeline Bootstrap`

This handoff is based on repository files, current scripts, generated outputs, git status, and validation commands from this thread. Do not rely on older chat history.

## 1. Scope Classification

scope classification: `energy-only pipeline bootstrap using account-generic infrastructure`

This version bootstraps the energy account research pipeline. It is not tech-only, not controller-summary, not provider runtime hardening, not energy trading logic, not energy minute/intraday/VWAP work, and not a commodity realtime framework.

## 2. Completed Work

- Added `scripts/run_energy_operation_candidates.ps1`.
- Added `scripts/run_energy_watchlist.ps1`.
- Added `scripts/run_energy_scan.ps1`.
- Added `scripts/run_energy_research_pipeline.ps1`.
- Updated `scripts/run_energy_fast_strict.ps1` to use `--profile energy --universe energy_core`.
- Added account-aware energy layer manifest support for `energy_core`, `energy_operation_candidates`, `energy_watchlist`, and `energy_scan`.
- Kept strict, `usable_for_operation`, `quote_trust_tier`, provider priority, YFinance circuit behavior, AKShare/Eastmoney/YFinance routing, config files, positions, costs, gold amount, and controller denominator unchanged.
- Added an energy UAT profile in `scripts/run_uat.ps1`; it runs the energy research pipeline as the profile check.
- Added tests for energy script contracts, energy layer manifest counts, energy report generation, and energy UAT declaration.
- Generated independent energy outputs and pipeline outputs.

## 3. Energy Pipeline Scripts

- `scripts/run_energy_fast_strict.ps1`
- `scripts/run_energy_operation_candidates.ps1`
- `scripts/run_energy_watchlist.ps1`
- `scripts/run_energy_scan.ps1`
- `scripts/run_energy_research_pipeline.ps1`

Pipeline order:

1. `energy_scan`
2. `energy_watchlist`
3. `energy_operation_candidates`
4. `energy_fast_strict`

The pipeline does not include minute_probe, intraday_metrics, or VWAP.

## 4. Energy Outputs

- `outputs_energy_latest`
- `outputs_energy_operation_candidates_latest`
- `outputs_energy_watchlist_latest`
- `outputs_energy_scan_latest`
- `outputs_energy_pipeline_latest`

Each layer output includes:

- `prices_snapshot.csv`
- `layer_manifest.json`
- `0_upload_bundle.md`
- `data_completeness_report.md`
- `runtime_diagnostics.md`
- `debug_bundle.md`

Pipeline output includes:

- `pipeline_summary.md`
- `pipeline_manifest.json`
- `pipeline_layer_manifest.json`
- `upload_manifest.md`

## 5. Current Energy Layer Counts

| layer | configured | loaded | mismatch |
|---|---:|---:|---|
| energy_scan | 41 | 41 | false |
| energy_watchlist | 24 | 24 | false |
| energy_operation_candidates | 8 | 8 | false |
| energy_core | 4 | 4 | false |

All energy layer manifests include:

- `account: energy`
- `root_mirror_match: true`
- `account_bootstrapped: true`
- `config_mismatch: false`

## 6. Current Energy Data Completeness

Latest `outputs_energy_pipeline_latest/pipeline_summary.md`:

| layer | total | success | failed | provider_missing | unsupported | stale | usable_reference | usable_operation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| energy_scan | 41 | 4 | 37 | 0 | 0 | 41 | 0 | 0 |
| energy_watchlist | 24 | 4 | 20 | 0 | 0 | 24 | 0 | 0 |
| energy_operation_candidates | 8 | 0 | 8 | 0 | 0 | 8 | 0 | 0 |
| energy_fast_strict | 4 | 4 | 0 | 0 | 0 | 4 | 0 | 0 |

Provider/data warnings:

- Energy fast strict generated reports but returned strict status `2`, summarized by the pipeline as `strict_blocked_but_reported`.
- The four operation symbols loaded correctly: `00883.HK`, `601899.SH`, `601985.SH`, `003816.SZ`.
- The four operation symbols currently selected stale `mock_fallback` records and are not operation-ready.
- Reference layers completed without blocking operation strict.
- Scan/watchlist/candidate failures or stale records do not promote symbols and do not affect operation-ready status.
- Runtime budget warnings remain for slower live provider steps.

## 7. Tech Status

Tech counts remain unchanged:

| layer | count |
|---|---:|
| operation | 7 |
| operation_candidate | 11 |
| watchlist | 16 |
| scan | 30 |

Tech compatibility validation:

- `.\scripts\check_account_layer_config.ps1 -Account tech`: exit `0`.
- `.\scripts\check_tech_layer_config.ps1`: exit `0`.
- `.\scripts\manage_account_layers.ps1 -Account tech show`: exit `0`.
- `.\scripts\manage_tech_layers.ps1 show`: exit `0`.
- `.\scripts\manage_tech_layers.ps1 validate`: exit `0`.
- `.\scripts\manage_tech_layers.ps1 export`: exit `0`.
- `.\scripts\run_tech_research_pipeline.ps1 -UseRunCache`: exit `0`; summary shows `passed: 6`, `failed: 0`.
- `.\scripts\run_uat.ps1 -Mode quick -UseRunCache`: exit `0`.
- `.\scripts\run_uat.ps1 -Mode intraday -UseRunCache`: exit `0`.

No energy symbols were added to tech config. No tech config files were changed.

## 8. Explicit Non-Goals

This version did not implement:

- minute_probe
- intraday_metrics
- VWAP
- energy trading logic
- commodity realtime framework
- QDII premium
- NDX/QQQ/FX reference work
- advice layer
- `action_hint`
- `preferred_action`
- automatic scan/watchlist/candidate promotion
- provider runtime hardening
- UI

## 9. Validation Results

- `pytest`: `337 passed`.
- `.\scripts\check_account_layer_config.ps1 -Account energy`: exit `0`.
- `.\scripts\run_energy_fast_strict.ps1`: exit `2`, strict-blocked but reports generated.
- `.\scripts\run_energy_operation_candidates.ps1`: exit `0`.
- `.\scripts\run_energy_watchlist.ps1`: exit `0`.
- `.\scripts\run_energy_scan.ps1`: exit `0`.
- `.\scripts\run_energy_research_pipeline.ps1`: exit `0`.
- `.\scripts\run_uat.ps1 -Mode energy -UseRunCache`: exit `0`.
- `git diff -- config`: no diff.
- No-advice keyword scan over requested energy and tech pipeline Markdown outputs: no matches.

UAT note: quick/intraday UAT were rerun sequentially after an earlier parallel invocation caused run-cache write contention in console output. The sequential UAT runs exited `0`.

## 10. Acceptance Commands

```powershell
pytest
.\scripts\check_account_layer_config.ps1 -Account energy
Get-Content outputs_config_check_latest\energy_layer_config_check.md -Encoding UTF8
.\scripts\run_energy_fast_strict.ps1
Get-Content outputs_energy_latest\layer_manifest.json -Encoding UTF8
Get-Content outputs_energy_latest\data_completeness_report.md -Encoding UTF8
.\scripts\run_energy_operation_candidates.ps1
Get-Content outputs_energy_operation_candidates_latest\layer_manifest.json -Encoding UTF8
.\scripts\run_energy_watchlist.ps1
Get-Content outputs_energy_watchlist_latest\layer_manifest.json -Encoding UTF8
.\scripts\run_energy_scan.ps1
Get-Content outputs_energy_scan_latest\layer_manifest.json -Encoding UTF8
.\scripts\run_energy_research_pipeline.ps1
Get-Content outputs_energy_pipeline_latest\pipeline_summary.md -Encoding UTF8
Get-Content outputs_energy_pipeline_latest\pipeline_layer_manifest.json -Encoding UTF8
.\scripts\check_account_layer_config.ps1 -Account tech
.\scripts\check_tech_layer_config.ps1
.\scripts\manage_tech_layers.ps1 validate
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
.\scripts\run_uat.ps1 -Mode energy -UseRunCache
git diff -- config
Select-String -Path `
  outputs_energy_pipeline_latest\*.md,`
  outputs_energy_latest\*.md,`
  outputs_energy_operation_candidates_latest\*.md,`
  outputs_energy_watchlist_latest\*.md,`
  outputs_energy_scan_latest\*.md,`
  outputs_tech_pipeline_latest\*.md `
  -Pattern "买入|卖出|加仓|减仓|做T|挂单|目标价|入场价|止损|preferred_action|action_hint|buy|sell|add|reduce" `
  -CaseSensitive:$false
```

## 11. Strictly Forbidden For Next Thread Unless Explicitly Scoped

- Do not output trading advice.
- Do not modify positions, cost basis, cash, gold amount, or controller denominator.
- Do not mix tech and energy layer configs.
- Do not promote scan/watchlist/candidate symbols automatically.
- Do not apply tech strategy rules to energy by default.
- Do not change provider priority, strict semantics, `usable_for_operation`, or `quote_trust_tier` semantics.
- Do not add energy minute_probe, intraday_metrics, or VWAP unless a future version explicitly scopes it.
- Do not implement commodity realtime inference unless explicitly scoped.

## 12. Next Version Suggestions

Recommended next version:

`v0.7.4.4 | Energy Pipeline Report Polish / Energy UAT Profile`

Alternative later version:

`v0.7.5 | Provider Runtime Budget Hardening for Multi-Account`

Do not implement either inside v0.7.4.3.

## 13. Next Thread Should Read First

- `docs/ACCOUNT_ARCHITECTURE.md`
- `docs/HANDOFF_v0.7.4.3.md`
- `docs/HANDOFF_v0.7.4.2.md`
- `scripts/run_energy_research_pipeline.ps1`
- `scripts/run_energy_fast_strict.ps1`
- `scripts/run_energy_operation_candidates.ps1`
- `scripts/run_energy_watchlist.ps1`
- `scripts/run_energy_scan.ps1`
- `scripts/manage_account_layers.ps1`
- `scripts/check_account_layer_config.ps1`
- `config/watchlist.yaml`
- `config/universes/energy_core.yaml`
- `config/universes/energy_operation_candidates.yaml`
- `config/universes/energy_watchlist.yaml`
- `config/universes/energy_scan.yaml`
- `config/symbol_registry.yaml`
