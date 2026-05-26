# UAT Runtime Profiles

market_price_guard is not tech-only. Current quick and intraday UAT coverage is still mostly tech account coverage; future account-generic UAT should keep tech and energy checks isolated instead of mixing account configs or outputs.

`scripts/run_uat.ps1` supports three runtime profiles:

| mode | purpose | typical use |
|---|---|---|
| quick | Fast default acceptance that skips heavy live provider diagnostics. | Small fixes and daily development checks. |
| intraday | Minute probe and reference intraday metrics acceptance. | Minute bars / reference VWAP development. |
| full | Complete live provider regression. | Important releases or pre-publish checks. |

## Commands

```powershell
.\scripts\run_uat.ps1
.\scripts\run_uat.ps1 -Mode quick
.\scripts\run_uat.ps1 -Mode intraday
.\scripts\run_uat.ps1 -Mode full
```

Default mode is `quick`.

## Included Items

`quick` runs:

- `tech_fast_strict`
- `tech_operation_candidates`
- `tech_intraday_metrics`
- `mock_strict`

`intraday` runs:

- `tech_fast_strict`
- `tech_operation_candidates`
- `tech_minute_probe` with the default `MinuteMode=balanced`
- `tech_intraday_metrics`
- `mock_strict`

`full` runs all defined UAT items, including diagnostic, reconcile, scan, energy, all/controller, minute probe, and reference intraday metrics.

## Summary Semantics

- `skipped_by_profile` means the selected mode intentionally skipped the item. It is not a failure.
- `strict_blocked_but_reported` is not a failure when reports are generated and blocking is explained.
- `failed=0` returns exit code `0`.
- Invalid mode returns exit code `1`.

## Notes

Heavy live provider items such as diagnostic, reconcile, scan_ai, energy, and all/controller are no longer part of the default quick run.

This profile split does not add shared provider cache, cross-script cache, provider cache, provider timeout hard kill, or provider behavior changes. A shared provider cache can be handled by a separate future version such as `v0.7.2c.1`.

## Optional UAT Run Cache

`v0.7.2c.1` adds an opt-in UAT run cache:

```powershell
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
.\scripts\run_uat.ps1 -Mode full -UseRunCache
```

The cache remains off by default. The first probe only caches `akshare.fund_etf_spot_em` inside the current UAT run directory `outputs_uat_run_cache_latest`.

It does not cache minute bars, YFinance, Eastmoney Direct, AKShare stock helpers, AKShare HK helpers, diagnostic exhaustive calls, operation readiness, VWAP, or advice/action outputs. Cache hits do not change freshness, strict, quote trust tier, usable_for_operation, or operation/reference semantics.

See [uat_run_cache.md](uat_run_cache.md) for details.

## Runtime Modes

See [runtime_modes.md](runtime_modes.md) for v0.7.3 scan and minute runtime modes.

- `run_tech_scan_ai.ps1` defaults to `Mode=fast`.
- `run_tech_minute_probe.ps1` defaults to `Mode=balanced`.
- `run_tech_research_pipeline.ps1` defaults to `ScanMode=fast`, `MinuteMode=balanced`, and `MinuteWorkers=3`.
