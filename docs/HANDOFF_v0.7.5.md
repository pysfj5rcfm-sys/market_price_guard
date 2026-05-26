# HANDOFF v0.7.5

Version: `v0.7.5 | Multi-Account Provider Runtime Budget Hardening`

Scope classification: `account-generic provider runtime hardening`

This version is not tech-only, not energy-only, not controller-summary, not QDII premium, not a commodity realtime framework, not trading logic, and not UI.

## Completed

- Organized provider runtime budget as account-generic runtime infrastructure shared by tech and energy.
- Passed the run-level `ProviderRuntimeBudget` into runtime diagnostics so per-provider attempts, elapsed seconds, slow attempts, failures, timeouts, skipped-by-budget counts, and circuit state are visible in reports.
- Added provider circuit state for providers that exceed timeout/failure thresholds in the same run.
- Kept planned provider chain distinct from actual provider attempts.
- Kept skipped providers out of `actual_provider_attempted`.
- Added `route_reason` to per-symbol provider diagnostics.
- Added a unified `Provider Health Summary` table to provider health reports.
- Added a unified `Provider Runtime Summary` section to runtime diagnostics.
- Added `Runtime Budget Summary` and `Provider Health Summary` sections to tech and energy pipeline summaries.
- Fixed UAT summary overwrite by writing mode-specific summaries under `outputs_uat_latest/<mode>/` while retaining root latest summary.
- Updated tests for provider planned/actual/skip semantics, runtime circuit behavior, provider health summary fields, and UAT output contracts.
- Added generated `outputs_uat_summary.md` to `.gitignore`.

## Provider Runtime Budget Implementation

The account-generic runtime budget lives in `src/market_price_guard/provider_router.py` as `ProviderRuntimeBudget`.

Key tracked fields:

- `account`
- `run_id`
- `timeout_seconds`
- `max_time_seconds_by_provider`
- `max_attempts_by_provider`
- `timeout_threshold`
- `failure_threshold`
- `attempts_by_provider`
- `elapsed_by_provider`
- `slow_attempts_by_provider`
- `failed_attempts_by_provider`
- `timeout_attempts_by_provider`
- `skipped_by_budget_by_provider`
- `circuit_open_by_provider`

Tech and energy both use the same structure from `run_pipeline()`. AKShare is no longer capped at one successful attempt because tech ETF operation paths need repeated normal AKShare calls. Slow/failed provider paths are still bounded by timeout, failure, and elapsed budgets.

## Planned vs Actual Provider Attempts

Per-symbol diagnostics now preserve these meanings:

- `provider_planned_chain`: provider chain planned by route resolver.
- `actual_provider_attempted`: providers that were actually called.
- `provider_skip_reasons`: planned providers skipped by policy, budget, or circuit.
- `selected_provider`: selected from an actual provider attempt, manual path, or explicit mock fallback.

Skipped providers are not counted as actual attempts.

## Provider Skip Reasons

Unified skip/failure reasons include:

- `selected_provider_success_policy_skip`
- `provider_skipped_by_runtime_budget`
- `provider_skipped_by_failure_budget`
- `skipped_by_provider_circuit`
- `fallback_skipped_yfinance_circuit_open`
- `hk_akshare_skipped_after_fast_provider_failure_budget`
- `provider_not_configured`
- `provider_timeout`
- `provider_exception`
- `symbol_not_found`
- `mock_fallback_not_allowed`

Mock fallback remains development-only and not usable for reference or operation.

## Provider Health Report Fields

`provider_health_report.md` now includes a common `Provider Health Summary` table:

- `provider`
- `planned_count`
- `actual_attempt_count`
- `success_count`
- `failure_count`
- `timeout_count`
- `skipped_count`
- `elapsed_seconds`
- `slow_attempt_count`
- `top_failure_reasons`

Per-symbol diagnostics include:

- `normalized_symbol`
- `route_reason`
- `provider_planned_chain`
- `actual_provider_attempted`
- `provider_skip_reasons`
- `selected_provider`
- `quote_trust_tier`
- `usable_for_reference`
- `usable_for_operation`
- failure/blocking reason fields

## Tech Current Provider Runtime State

Tech layer counts remain:

- operation: `7`
- operation_candidate: `11`
- watchlist: `16`
- scan: `30`

Latest validation:

- `run_tech_research_pipeline.ps1 -UseRunCache`: exit `0`
- passed: `6`
- failed: `0`
- layer config mismatch: `false`

Runtime remains provider/network dependent. Latest local tech pipeline took about `290s`; the summary now surfaces slow steps and provider budget/circuit counts instead of hiding the cause.

## Energy Current Provider Runtime State

Energy layer counts remain:

- operation: `4`
- operation_candidate: `8`
- watchlist: `24`
- scan: `41`

Latest validation:

- `run_energy_research_pipeline.ps1`: exit `0`
- passed: `3`
- strict_blocked_but_reported: `1`
- failed: `0`
- layer config mismatch: `false`

Energy operation strict remains blocked when only mock/development/reference-tier quotes are available. This is expected and reported, not treated as a pipeline failure.

## UAT Summary Output Structure

UAT now writes:

```text
outputs_uat_latest/
  quick/
    outputs_uat_summary.md
    outputs_uat_summary.json
  intraday/
    outputs_uat_summary.md
    outputs_uat_summary.json
  energy/
    outputs_uat_summary.md
    outputs_uat_summary.json
  uat_run_manifest.json
```

The root `outputs_uat_summary.md` remains as latest summary only. Mode-specific summaries are retained and no longer overwrite each other.

Latest local UAT results:

- quick: run_count `4`, passed `2`, strict_blocked_but_reported `2`, failed `0`
- intraday: run_count `5`, passed `3`, strict_blocked_but_reported `2`, failed `0`
- energy: run_count `1`, passed `1`, strict_blocked_but_reported `0`, failed `0`

## Config And Strict Semantics

- No tech or energy universe config was modified.
- `git diff -- config` was empty.
- Strict was not relaxed.
- `usable_for_operation` semantics were not changed.
- `quote_trust_tier` semantics were not changed.
- Mock/stale/development quotes remain not usable for operation.
- Eastmoney Direct remains reference-tier / confirmation-required, not operation-grade by itself.

## Not Implemented

- No trading logic.
- No action fields.
- No QDII premium framework.
- No commodity realtime framework.
- No oil/copper/gold realtime derivation.
- No energy minute probe.
- No energy intraday metrics.
- No energy VWAP.
- No automatic symbol promotion between scan/watchlist/operation_candidate/operation.
- No config changes.

## Validation Commands

```powershell
pytest
.\scripts\check_account_layer_config.ps1 -Account tech
.\scripts\check_account_layer_config.ps1 -Account energy
.\scripts\check_tech_layer_config.ps1
.\scripts\manage_account_layers.ps1 -Account tech show
.\scripts\manage_account_layers.ps1 -Account energy show
.\scripts\manage_account_layers.ps1 -Account energy validate
.\scripts\manage_account_layers.ps1 -Account energy export
.\scripts\manage_tech_layers.ps1 show
.\scripts\manage_tech_layers.ps1 validate
.\scripts\manage_tech_layers.ps1 export
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
.\scripts\run_energy_research_pipeline.ps1
.\scripts\run_energy_fast_strict.ps1
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
.\scripts\run_uat.ps1 -Mode energy -UseRunCache
git diff -- config
```

`pytest`: `347 passed`.

No-advice output scan over generated tech/energy markdown reports returned no matches for the forbidden execution-action keyword pattern.

## Strict Prohibitions To Preserve

- Do not mix tech and energy symbols or rules.
- Do not let `-Account energy` fallback to tech.
- Do not relax strict.
- Do not mark mock/stale/development/provider_missing as usable.
- Do not output execution guidance.
- Do not implement action hints or preferred actions.
- Do not implement QDII premium in this version line unless explicitly scoped.
- Do not implement commodity realtime framework unless explicitly scoped.
- Do not modify positions, costs, cash, gold amount, or controller total assets.
- Do not promote symbols automatically across layers.

## Recommended Next Versions

- `v0.7.5.1 | Provider Coverage Polish`
- `v0.7.6 | QDII Premium Framework`
- `v0.7.6 | Energy Commodity Reference Framework`

Do not treat any of the above as implemented in v0.7.5.

## Next Thread Must Read

- `docs/ACCOUNT_ARCHITECTURE.md`
- `docs/HANDOFF_v0.7.5.md`
- `docs/HANDOFF_v0.7.4.4.md`
- `scripts/run_tech_research_pipeline.ps1`
- `scripts/run_energy_research_pipeline.ps1`
- `scripts/run_uat.ps1`
- provider / quote / runtime related modules
- `outputs_tech_pipeline_latest/pipeline_summary.md`
- `outputs_energy_pipeline_latest/pipeline_summary.md`
