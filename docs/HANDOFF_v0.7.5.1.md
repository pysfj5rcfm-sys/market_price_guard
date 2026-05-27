# HANDOFF v0.7.5.1

Version: `v0.7.5.1 | Provider Coverage Polish + Slow Path Reduction`

Scope classification: `account-generic provider coverage polish + slow path reduction`

This version is not tech-only, not energy-only, not controller-summary, not Provider Expansion, not QDII premium, not commodity realtime framework, not trading logic, and not UI.

## Completed

- Added account-generic run-level quote cache in `src/market_price_guard/quote_run_cache.py`.
- Integrated quote cache into `route_symbol()` so repeated symbols across one pipeline run can reuse success and failure results.
- Cache hits keep `actual_provider_attempted=[]` and `provider_attempts=[]`, so they do not count as new provider attempts.
- Cache keys include account, normalized symbol, quote purpose, provider profile, runtime profile, market, and asset type.
- Operation quote requests do not directly consume reference quote cache. They report `cache_hit_but_profile_insufficient` and retry the operation route.
- Expanded AKShare UAT/run batch cache handling from only `fund_etf_spot_em` to the project batch functions used by ETF, A-share, and HK paths.
- AKShare batch failures can be cached by function and reused in the same run to prevent repeated slow failure.
- Shortened Eastmoney Direct default timeout and retry behavior.
- Classified Eastmoney Direct permission failures such as `WinError 10013` as `provider_network_permission_denied`.
- Opened run-level provider circuit after Eastmoney Direct environment permission failures.
- Preserved HK bounded route semantics. HK failures remain HK-specific, such as `hk_reference_unavailable`, instead of collapsing to generic A-share not-found.
- Added `Cache / Reuse Summary` to runtime diagnostics and pipeline summaries.
- Extended Provider Health Summary with cache/circuit/repeated-call fields.
- Updated tests for current repository layer counts and cache behavior.

## Run-Level Quote Cache

Implementation file: `src/market_price_guard/quote_run_cache.py`.

The cache is enabled by:

- `MARKET_GUARD_USE_QUOTE_RUN_CACHE=1`
- `MARKET_GUARD_QUOTE_RUN_CACHE_DIR=<pipeline quote cache dir>`

Pipeline scripts now create fresh quote cache dirs:

- `outputs_tech_pipeline_quote_cache_latest`
- `outputs_energy_pipeline_quote_cache_latest`

Quote cache key fields:

- `account`
- `symbol`
- `normalized_symbol`
- `quote_purpose`
- `provider_profile`
- `runtime_profile`
- `market`
- `asset_type`

Layer is retained as source metadata, but not part of the filename key, so scan/watchlist/candidate layers can reuse within the same account/purpose/profile.

## Success And Failure Cache Semantics

- Success results are cached.
- Failure results are cached.
- Mock/stale/development results can be cached but do not become usable.
- Cache hit records set `cache_hit=true`, `cache_miss=false`, `repeated_provider_call_prevented=true`.
- Cache hits keep `actual_provider_attempted=[]`.
- Source provider attempts are preserved under `source_provider_attempts` for traceability.
- Different accounts do not share quote result cache.
- Reference cache does not upgrade operation cache. Operation requests retry and record `cache_hit_but_profile_insufficient`.

## AKShare Batch Cache

The existing AKShare in-process batch cache remains.

The UAT/run cache now recognizes:

- `fund_etf_spot_em`
- `stock_zh_a_spot_em`
- `stock_sh_a_spot_em`
- `stock_sz_a_spot_em`
- `stock_hk_spot_em`
- `stock_hk_main_board_spot_em`
- `stock_hsgt_sh_hk_spot_em`

Behavior:

- Batch success is cached per function.
- Batch failure writes a per-function failure cache marker.
- Later calls in the same run can return cached failure status instead of repeating the slow batch call.
- Runtime diagnostics report batch hit/miss/reuse/failure-cached counts.

## Eastmoney Direct Timeout And Circuit

Eastmoney Direct now defaults to shorter live behavior:

- `timeout_seconds=2.5`
- `max_retries=0`

Failure classification:

- Permission/socket policy errors: `provider_network_permission_denied`
- Timeout-like errors: `provider_timeout`
- Other provider failures: `provider_error`

When Eastmoney Direct reports `provider_network_permission_denied`, the run-level runtime budget opens the provider circuit. Later symbols report `skipped_by_provider_circuit` instead of repeating the environment failure.

## HK Bounded Route

HK route remains bounded:

- Fast HK route tries yfinance first.
- If yfinance fails in fast mode, AKShare HK path can be skipped by the fast HK budget guard.
- HK final failures are HK-specific, e.g. `hk_reference_unavailable` or `hk_provider_timeout`.
- HK mock fallback remains development-only and unusable.

## Cache / Reuse Summary Fields

Runtime diagnostics and pipeline summary now include:

- `quote_cache_hit_count`
- `quote_cache_miss_count`
- `quote_cache_failure_hit_count`
- `quote_cache_success_hit_count`
- `batch_cache_hit_count`
- `batch_cache_miss_count`
- `batch_provider_reuse_count`
- `batch_provider_failure_cached_count`
- `repeated_provider_call_prevented_count`
- `repeated_batch_call_prevented_count`
- `cache_hit_by_layer`
- `cache_hit_by_provider`
- `quote_cache_profile_insufficient_count`

Provider Health Summary now includes:

- `cache_hit_count`
- `cache_miss_count`
- `failure_cached_count`
- `circuit_open_count`
- `repeated_call_prevented_count`

## Tech Runtime State

Current tech counts from repository config:

- operation: `7`
- operation_candidate: `19`
- watchlist: `28`
- scan: `40`

Latest tech research pipeline:

- command: `.\scripts\run_tech_research_pipeline.ps1 -UseRunCache`
- exit: `0`
- passed: `6`
- failed: `0`
- total_elapsed_seconds: `142.039`
- quote_cache_hit_count: `70`
- quote_cache_failure_hit_count: `55`
- repeated_provider_call_prevented_count: `70`

This is materially lower than the v0.7.5 handoff runtime near `290s`. Remaining slow steps are `tech_scan_ai` and `tech_minute_probe`.

## Energy Runtime State

Current energy counts:

- operation: `4`
- operation_candidate: `8`
- watchlist: `24`
- scan: `41`

Latest energy pipeline after UAT energy:

- command: `.\scripts\run_energy_research_pipeline.ps1`
- exit: `0`
- passed: `3`
- strict_blocked_but_reported: `1`
- failed: `0`
- total_elapsed_seconds: `126.393`
- quote_cache_hit_count: `32`
- quote_cache_failure_hit_count: `28`
- repeated_provider_call_prevented_count: `32`

An earlier standalone energy pipeline in the same validation sequence completed in `7.211s`; the later UAT energy run hit slower live provider paths but still prevented repeated layer-level failures.

## UAT Summary Structure

Mode-specific UAT summary structure is preserved:

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

Latest UAT:

- quick: exit `0`
- intraday: exit `0`
- energy: exit `0`

## Config And Strict Semantics

- This version did not intentionally edit config files.
- Important handoff caveat: the worktree already had config diffs when this thread started, and `git diff -- config` remains non-empty because of those pre-existing changes.
- Strict was not relaxed.
- `usable_for_operation` semantics were not changed.
- `quote_trust_tier` semantics were not changed.
- Mock/stale/development/provider-missing outputs remain unusable for operation.

## Not Implemented

- No trading logic.
- No action fields.
- No QDII premium framework.
- No commodity realtime framework.
- No oil/copper/gold realtime derivation.
- No energy minute probe.
- No energy intraday metrics.
- No energy VWAP.
- No automatic symbol promotion between layers.
- No new large provider.

## Validation

Commands run:

```powershell
pytest
.\scripts\check_account_layer_config.ps1 -Account tech
.\scripts\check_account_layer_config.ps1 -Account energy
.\scripts\check_tech_layer_config.ps1
.\scripts\manage_account_layers.ps1 -Account tech show
.\scripts\manage_tech_layers.ps1 show
.\scripts\manage_tech_layers.ps1 validate
.\scripts\manage_tech_layers.ps1 export
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
.\scripts\run_energy_research_pipeline.ps1
.\scripts\run_energy_fast_strict.ps1
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
.\scripts\run_uat.ps1 -Mode energy -UseRunCache
Get-ChildItem -Recurse outputs_uat_latest | Select-Object FullName
git diff -- config
Select-String ... no-advice pattern
```

Results:

- `pytest`: `351 passed`
- tech config checks: exit `0`
- energy config check: exit `0`
- tech pipeline: exit `0`
- energy pipeline: exit `0`
- energy fast strict: exit `2`, expected strict block with reports generated
- UAT quick/intraday/energy: exit `0`
- no-advice output scan: no matches

## Strict Prohibitions To Preserve

- Do not mix tech and energy symbols or rules.
- Do not let `-Account energy` fallback to tech.
- Do not relax strict.
- Do not mark mock/stale/development/provider-missing as usable.
- Do not implement execution action fields.
- Do not implement QDII premium inside this version line.
- Do not implement commodity realtime framework inside this version line.
- Do not modify positions, costs, cash, gold amount, or controller total assets.
- Do not promote symbols automatically across layers.

## Remaining Issues

- `tech_scan_ai` still exceeds the nominal 30s runtime budget in live conditions.
- `tech_minute_probe` remains slow and is outside the quote-cache-only scope.
- Energy live runtime remains network-dependent. Later UAT energy took about `126s` because some provider paths were slow, despite cache/circuit preventing repeated layer-level calls.
- Energy real quote coverage is still weak and should be addressed by a future scoped provider coverage version, not by relaxing strict.

## Suggested Next Versions

- `v0.7.5.2 | Provider Coverage Polish Follow-up`
- `v0.7.6 | QDII Premium Framework`
- `v0.7.6 | Energy Commodity Reference Framework`

Do not treat any of these as implemented in v0.7.5.1.

## Next Thread Must Read

- `docs/ACCOUNT_ARCHITECTURE.md`
- `docs/HANDOFF_v0.7.5.1.md`
- `docs/HANDOFF_v0.7.5.md`
- `scripts/run_tech_research_pipeline.ps1`
- `scripts/run_energy_research_pipeline.ps1`
- `scripts/run_uat.ps1`
- provider / quote / runtime related modules
- `outputs_tech_pipeline_latest/pipeline_summary.md`
- `outputs_energy_pipeline_latest/pipeline_summary.md`
