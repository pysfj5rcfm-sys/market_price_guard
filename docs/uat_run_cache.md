# UAT Run Cache

`run_uat.ps1` supports an opt-in run-scoped cache:

```powershell
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
.\scripts\run_uat.ps1 -Mode full -UseRunCache
```

The cache is off by default. A normal script run such as `run_tech_fast_strict.ps1` does not use this cache unless it is launched by `run_uat.ps1 -UseRunCache`.

## Scope

The first probe caches only:

- provider: `akshare`
- function: `fund_etf_spot_em`
- scope: one UAT run
- directory: `outputs_uat_run_cache_latest`

Files:

- `cache_manifest.json`
- `akshare_fund_etf_spot_em.csv`

Every `-UseRunCache` UAT run recreates the cache directory. The cache is not global, not permanent, and not reused across UAT runs.

## Not Cached

This version does not cache minute bars, YFinance, Eastmoney Direct, AKShare stock helpers, AKShare HK helpers, diagnostic exhaustive calls, operation readiness results, VWAP results, or any advice/action result.

## Semantics

The run cache only reduces repeated provider fetches. It does not change freshness, stale checks, strict, quote trust tier, usable_for_operation, operation/reference semantics, or output permissions.

A cache hit may still produce stale data if the cached provider payload contains stale timestamps. The normal guard checks still apply.

## Reporting

`outputs_uat_summary.md` includes:

- `use_run_cache`
- `run_cache_dir`
- `cache_hit_count`
- `cache_miss_count`
- `cache_bypass_count`
- `cache_error_count`
- `estimated_cache_saved_calls`

Provider attempts in generated reports include `cache_enabled`, `cache_scope`, `cache_status`, and `cache_file` when the UAT run cache is involved.
