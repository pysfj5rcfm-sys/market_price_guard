# HANDOFF v0.7.4.4

Version: `v0.7.4.4 | Energy Provider Coverage & Runtime Diagnostics`

Scope classification: `energy-only provider coverage + runtime diagnostics`

This version diagnoses and improves energy account quote provider routing and runtime reporting. It is not tech-only, not controller-summary, not config layer expansion, not energy trading logic, not energy minute/intraday/VWAP work, not a commodity realtime framework, and not a QDII premium framework.

## Completed

- Made A-share stock detection account-generic for `.SH` / `.SZ` stock symbols instead of relying only on a small hardcoded energy symbol set.
- Added Eastmoney Direct as the fast reference path for energy A-share stocks.
- Extended Eastmoney Direct support from a fixed symbol allowlist to generic A-share / ETF symbol handling.
- Added per-run provider runtime budget tracking and bounded retries for energy provider routes.
- Added fast-path HK budget handling so `00883.HK` reports explicit provider failure / timeout state instead of repeatedly dragging AKShare HK paths.
- Added diagnostics for planned provider chain, actual attempted providers, skip reasons, normalized symbol, selected provider, and final failure reason.
- Added provider runtime budget output: per-provider elapsed seconds, per-symbol elapsed seconds, slow provider attempts, skipped-by-budget counts, timeout counts, and account-level summary.
- Kept mock fallback as development-only and unusable for both reference and operation selection.
- Kept energy strict behavior unchanged: operation output remains blocked when only mock/stale/development quotes are available.
- Kept tech pipeline and tech layer management compatible.

## Energy Provider Coverage Current State

Energy A-share symbols now plan `eastmoney_direct` before the slower fallback providers in fast/reference routes. When Eastmoney Direct is reachable, A-share energy symbols can return reference-grade quotes. When the local/network environment blocks Eastmoney Direct, reports now show provider error/timeout instead of a generic unknown failure.

Latest generated `outputs_energy_pipeline_latest/pipeline_summary.md`:

- version: `v0.7.4.4`
- passed: `3`
- strict_blocked_but_reported: `1`
- failed: `0`
- loaded counts: `41 / 24 / 8 / 4`
- config mismatch: `false`
- latest total elapsed: `9.305s` in bundled fallback environment

An energy UAT run using the live environment completed with total pipeline elapsed `233.791s`, below the prior 300s+ drag pattern, while preserving strict blocked reporting.

## Energy Operation 4 Core Quote Status

Latest standalone `outputs_energy_latest/prices_snapshot.csv`:

| symbol | selected_provider | quote_trust_tier | usable_for_reference | usable_for_operation |
|---|---|---|---|---|
| 00883.HK | mock | development | false | false |
| 601899.SH | mock | development | false | false |
| 601985.SH | mock | development | false | false |
| 003816.SZ | mock | development | false | false |

All four are strict-blocked in the latest local run because real provider attempts were unavailable or failed under the current environment. This is reported as `strict_blocked_but_reported`, not as operation-ready.

## Energy A-share Provider Route

- A-share energy stocks such as `601899.SH`, `601985.SH`, `003816.SZ`, `600938.SH`, `600900.SH`, `601088.SH`, and similar `.SH` / `.SZ` stocks now route through the non-tech-only A-share quote path.
- Route diagnostics distinguish `provider_planned_chain` from `actual_provider_attempted`.
- A-share failures now surface provider-specific reasons such as provider timeout, provider error, skipped by runtime budget, or mock fallback not allowed.
- A-share failures should no longer collapse directly to generic `symbol_not_found` when a provider route exists.

## 00883.HK Provider State

`00883.HK` now has explicit HK diagnostics:

- planned chain includes HK-capable fallback routes.
- actual attempts and skipped providers are reported per symbol.
- fast HK AKShare retry is bounded after fast provider failure to avoid repeated slow HK calls.
- failure reason is reported as HK reference unavailable / provider timeout / provider error instead of plain generic not found.

## Mock Fallback And Strict Behavior

- `mock_fallback` remains development-only.
- `usable_for_reference=false`.
- `usable_for_operation=false`.
- strict operation remains blocked when only mock/stale/development quotes are available.
- strict semantics, `quote_trust_tier` semantics, and `usable_for_operation` semantics were not relaxed.
- reference outputs do not promote symbols into operation layers.

## Runtime Diagnostics

The following reports were enhanced or generated in each energy output directory:

- `data_completeness_report.md`
- `runtime_diagnostics.md`
- `provider_health_report.md`
- `debug_bundle.md`

Runtime diagnostics now include:

- per-provider elapsed seconds
- per-symbol elapsed seconds
- slow provider attempts
- provider timeout count
- skipped-by-runtime-budget count
- skipped-by-failure-budget count
- provider runtime budget summary
- run-time-budget-exceeded state

## Tech Status

Tech layer counts remain:

- operation: `7`
- operation_candidate: `11`
- watchlist: `16`
- scan: `30`

Tech pipeline validation:

- `run_tech_research_pipeline.ps1 -UseRunCache`: passed `6`, failed `0`
- `check_account_layer_config.ps1 -Account tech`: exit `0`
- `check_tech_layer_config.ps1`: exit `0`
- `manage_account_layers.ps1 -Account tech show`: exit `0`
- `manage_tech_layers.ps1 show/validate/export`: exit `0`

## Not Implemented In This Version

- No trading logic.
- No execution action fields.
- No energy minute probe.
- No energy intraday metrics.
- No energy VWAP.
- No commodity realtime framework.
- No QDII premium framework.
- No config layer changes.
- No automatic symbol promotion between layers.
- No tech/energy config mixing.

## Validation Commands Run

```powershell
pytest
.\scripts\run_energy_research_pipeline.ps1
.\scripts\run_energy_fast_strict.ps1
.\scripts\check_account_layer_config.ps1 -Account energy
.\scripts\check_account_layer_config.ps1 -Account tech
.\scripts\check_tech_layer_config.ps1
.\scripts\manage_account_layers.ps1 -Account tech show
.\scripts\manage_tech_layers.ps1 show
.\scripts\manage_tech_layers.ps1 validate
.\scripts\manage_tech_layers.ps1 export
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
.\scripts\run_uat.ps1 -Mode energy -UseRunCache
git diff -- config
```

Results:

- `pytest`: `345 passed`
- energy pipeline: exit `0`, strict blocked reported for operation
- energy fast strict: exit `2`, expected strict block
- tech pipeline: exit `0`, passed `6`, failed `0`
- UAT quick: exit `0`
- UAT intraday: exit `0`
- UAT energy: exit `0`
- `git diff -- config`: no diff
- no-advice output scan: no matches in generated pipeline markdown reports

## Strict Prohibitions To Preserve

- Do not change energy or tech layer config unless a future version explicitly scopes it.
- Do not mix tech symbols into energy or energy symbols into tech.
- Do not relax strict.
- Do not reinterpret mock/stale/development quotes as usable.
- Do not add execution logic or action fields.
- Do not add energy minute/intraday/VWAP unless explicitly scoped.
- Do not turn provider failures into investment signals.
- Do not promote scan/watchlist/operation_candidate symbols automatically.

## Recommended Next Version

Recommended next version:

`v0.7.4.5 | Energy Pipeline Report Polish`

Alternative later version:

`v0.7.5 | Multi-Account Provider Runtime Budget Hardening`

Do not implement either inside v0.7.4.4.

## Next Thread Must Read

- `docs/ACCOUNT_ARCHITECTURE.md`
- `docs/HANDOFF_v0.7.4.4.md`
- `docs/HANDOFF_v0.7.4.3.md`
- `scripts/run_energy_research_pipeline.ps1`
- `scripts/run_energy_fast_strict.ps1`
- `scripts/run_energy_operation_candidates.ps1`
- `scripts/run_energy_watchlist.ps1`
- `scripts/run_energy_scan.ps1`
- `scripts/run_tech_research_pipeline.ps1`
- `scripts/run_uat.ps1`
- `config/watchlist.yaml`
- `config/universes/energy_core.yaml`
- `config/universes/energy_operation_candidates.yaml`
- `config/universes/energy_watchlist.yaml`
- `config/universes/energy_scan.yaml`
- `config/symbol_registry.yaml`
