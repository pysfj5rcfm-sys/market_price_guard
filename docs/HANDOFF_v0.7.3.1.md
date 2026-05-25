# HANDOFF v0.7.3.1

This handoff is generated from the current repository state, committed history, scripts, docs, config files, and the presence or absence of current output directories. It is intended for a new Codex thread to continue from v0.7.3.1 without relying on prior chat context.

Generation-time repository facts:

- `git status --short` was clean before this handoff file was added.
- Latest commit: `1fa3261 polish reports and add yfinance circuit breaker`.
- Existing tag: `v0.7.3.1-report-polish-yfinance-circuit-pass`.
- Current output directories checked in the workspace root were not present at handoff generation time: `outputs_tech_pipeline_latest`, `outputs_tech_scan_ai_latest`, `outputs_tech_minute_probe_latest`, `outputs_tech_intraday_latest`, `outputs_tech_latest`, `outputs_tech_operation_candidates_latest`.
- `outputs_uat_summary.md` was not present at handoff generation time.
- Because outputs are currently absent, any runtime numbers, coverage counts, and provider success/failure states need verification by rerunning the commands in section 10.

## 1. Current Project State

`market_price_guard` is at the v0.7.3.1 stage in the committed history.

The v0.7.2 infrastructure stage is present in the repository:

- `tech_operation_candidates` exists as a reference-only operation-candidate universe.
- `run_tech_intraday_metrics.ps1` exists and produces reference intraday metrics from minute-probe artifacts.
- Minute probe can cover tech core and operation candidates.
- UAT has quick / intraday / full profiles.
- UAT and pipeline can use an opt-in run-scoped cache for `akshare.fund_etf_spot_em`.
- `run_tech_research_pipeline.ps1` orchestrates the tech research path.

The v0.7.3 Runtime & Coverage Stabilization stage is present:

- `run_tech_scan_ai.ps1` supports `-Mode fast|diagnostic`, default `fast`.
- Scan fast routes A-share scan stocks through Eastmoney Direct reference quotes.
- Scan fast skips slow AKShare stock exhaustive fallback.
- `run_tech_minute_probe.ps1` supports `-Mode fast|balanced|diagnostic`, default `balanced`.
- Minute balanced uses AKShare first, skips Eastmoney minute fallback, and uses YFinance reference fallback until a run-level circuit opens.
- `MinuteWorkers` is parsed and reported, but execution remains serial in the current implementation.
- Pipeline defaults are `ScanMode=fast`, `MinuteMode=balanced`, `MinuteWorkers=3`.

The v0.7.3.1 Report Consistency Polish + YFinance Circuit Breaker stage is committed:

- Scan upload bundles no longer leave `scan_mode` blank.
- Scan upload/report/runtime `run_time_budget_exceeded` uses the same runtime source.
- Minute debug/capability notes no longer claim minute bars are not implemented in v0.7.2a; current wording states minute bars are available through minute_probe when supported, reference-only, and not operation-grade.
- `diagnostic_only` is clarified as a provider capability label only; actual fallback behavior is controlled by `minute_mode`.
- `src/market_price_guard/yfinance_circuit.py` implements a run-only YFinance circuit breaker.
- Scan fast defaults to `yfinance_fallback_policy=disabled_in_fast_mode`.
- Minute balanced defaults to `yfinance_fallback_policy=enabled_until_circuit_open`.

Current main runtime chain:

1. `run_tech_scan_ai.ps1`
2. `run_tech_watchlist.ps1`
3. `run_tech_operation_candidates.ps1`
4. `run_tech_fast_strict.ps1`
5. `run_tech_minute_probe.ps1`
6. `run_tech_intraday_metrics.ps1`

The one-command orchestration script is `scripts/run_tech_research_pipeline.ps1`.

Expected output directories after running the pipeline:

- `outputs_tech_pipeline_latest`
- `outputs_tech_scan_ai_latest`
- `outputs_tech_watchlist_latest`
- `outputs_tech_operation_candidates_latest`
- `outputs_tech_latest`
- `outputs_tech_minute_probe_latest`
- `outputs_tech_intraday_latest`

These directories were not present at handoff generation time and should be regenerated before making runtime decisions.

## 2. Completed Versions Summary

Recent committed history from `git log --oneline -10`:

- `1fa3261 polish reports and add yfinance circuit breaker`
- `b4954d1 stabilize runtime modes and stock coverage`
- `5138920 add tech research pipeline runner`
- `2e5e3c0 add UAT run cache for AKShare ETF spot`
- `bd63d8c split UAT runtime profiles`
- `5cc6f59 include operation candidates in minute probe`
- `4425ce0 add tech operation candidate layer`
- `b7e1bcf slim upload bundle minute probe notes`
- `32c65cb add YFinance reference minute fallback`
- `4c29919 fix minute probe diagnostics`

Version summaries:

- v0.7.2a.2d Tech Operation Candidate Layer: committed as `4425ce0`. Adds `config/universes/tech_operation_candidates.yaml` and `scripts/run_tech_operation_candidates.ps1`. This layer is reference-only and does not affect core strict.
- v0.7.2b Reference VWAP + Intraday Position Basic: commit is not in the last 10 commits, but the implementation is present through `scripts/run_tech_intraday_metrics.ps1`, intraday output contract docs, and reference VWAP reporting code. Treat exact commit id as unknown unless searched further.
- v0.7.2b.1 Include Operation Candidates in Minute Probe: committed as `5cc6f59`. Minute probe covers tech core plus operation candidates.
- v0.7.2c UAT Runtime Profile Split: committed as `bd63d8c`. `run_uat.ps1` supports `quick`, `intraday`, and `full`.
- v0.7.2c.1 UAT Shared Provider Cache Probe: committed as `2e5e3c0`. Opt-in run cache caches only `akshare.fund_etf_spot_em`.
- v0.7.2c.2 Tech Research Pipeline Runner + Report Polish: committed as `5138920`. Adds `run_tech_research_pipeline.ps1` and pipeline summary/manifest behavior.
- v0.7.3 Runtime & Coverage Stabilization: committed as `b4954d1`. Adds scan/minute runtime modes, A-share scan Eastmoney reference coverage, and mode reporting.
- v0.7.3.1 Report Consistency Polish + YFinance Circuit Breaker: committed as `1fa3261`. Adds YFinance run-level circuit breaker and report consistency fixes.

## 3. Current Runtime Modes

### scan_ai

Script: `scripts/run_tech_scan_ai.ps1`

Supported calls:

```powershell
.\scripts\run_tech_scan_ai.ps1
.\scripts\run_tech_scan_ai.ps1 -Mode fast
.\scripts\run_tech_scan_ai.ps1 -Mode diagnostic
```

Current behavior:

- Default `Mode=fast`.
- `fast` keeps ETF / QDII ETF coverage on AKShare ETF batch where possible.
- `fast` routes A-share scan stocks, including `300308.SZ`, `300502.SZ`, and `688256.SH`, to Eastmoney Direct spot reference quote first.
- `fast` skips slow AKShare stock exhaustive fallback.
- `fast` disables YFinance fallback by default (`yfinance_fallback_policy=disabled_in_fast_mode`).
- `diagnostic` is for provider coverage troubleshooting and may attempt broader fallback.
- YFinance fallback in diagnostic mode is protected by the run-level circuit breaker.
- Eastmoney Direct scan stock quotes remain reference-only and do not become operation-grade.

### minute_probe

Script: `scripts/run_tech_minute_probe.ps1`

Supported calls:

```powershell
.\scripts\run_tech_minute_probe.ps1
.\scripts\run_tech_minute_probe.ps1 -Mode fast
.\scripts\run_tech_minute_probe.ps1 -Mode balanced
.\scripts\run_tech_minute_probe.ps1 -Mode diagnostic
.\scripts\run_tech_minute_probe.ps1 -Mode balanced -MinuteWorkers 3
```

Current behavior:

- Default `Mode=balanced`.
- `fast`: AKShare first; fallback is skipped by default when AKShare fails.
- `balanced`: AKShare first; if AKShare fails, skip Eastmoney minute fallback and try YFinance reference fallback until the YFinance circuit opens.
- `diagnostic`: AKShare -> Eastmoney Direct -> YFinance for troubleshooting; YFinance remains circuit-protected.
- `MinuteWorkers` is parsed and reported.
- Current implementation remains serial: `parallel_enabled=false`; reports state `workers parameter parsed, execution remains serial in this version`.
- Minute bars and derived metrics remain reference-only and do not change strict, quote trust tier, or usable_for_operation.

### pipeline

Script: `scripts/run_tech_research_pipeline.ps1`

Default step order:

1. `run_tech_scan_ai.ps1`
2. `run_tech_watchlist.ps1`
3. `run_tech_operation_candidates.ps1`
4. `run_tech_fast_strict.ps1`
5. `run_tech_minute_probe.ps1`
6. `run_tech_intraday_metrics.ps1`

Supported parameters:

- `-UseRunCache`
- `-StopOnFailure`
- `-SkipScan`
- `-SkipWatchlist`
- `-SkipOperationCandidates`
- `-SkipTechFast`
- `-SkipMinuteProbe`
- `-SkipIntradayMetrics`
- `-ScanMode fast|diagnostic`
- `-MinuteMode fast|balanced|diagnostic`
- `-MinuteWorkers <int>`

Defaults:

- `ScanMode=fast`
- `MinuteMode=balanced`
- `MinuteWorkers=3`
- `UseRunCache=false` unless explicitly passed.

With `-UseRunCache`, the pipeline uses `outputs_tech_pipeline_cache_latest` and the same run-cache environment variables currently used by UAT.

### UAT

Script: `scripts/run_uat.ps1`

Supported calls:

```powershell
.\scripts\run_uat.ps1
.\scripts\run_uat.ps1 -Mode quick
.\scripts\run_uat.ps1 -Mode intraday
.\scripts\run_uat.ps1 -Mode full
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
.\scripts\run_uat.ps1 -Mode full -UseRunCache
```

Modes:

- `quick`: default. Runs `tech_fast_strict`, `tech_operation_candidates`, `tech_intraday_metrics`, and `mock_strict`. Skips heavy live provider diagnostics.
- `intraday`: runs `tech_fast_strict`, `tech_operation_candidates`, `tech_minute_probe`, `tech_intraday_metrics`, and `mock_strict`. Intended for minute / reference VWAP development.
- `full`: runs all defined UAT items including diagnostic, reconcile, scan, energy, all/controller, minute probe, and intraday metrics. Can be slow.
- `-UseRunCache`: opt-in. Run cache remains off by default.

## 4. Current Config Layer Rules

Current universe files:

- `config/universes/tech_core.yaml`: tech core operation universe. Current symbols: `159632.SZ`, `513300.SH`, `159819.SZ`, `515880.SH`, `159516.SZ`, `510300.SH`, `GOLD_CNY`.
- `config/universes/tech_operation_candidates.yaml`: reference-only operation candidate universe. Current symbols: `159995.SZ`, `588200.SH`, `588170.SH`, `159558.SZ`.
- `config/universes/tech_watchlist.yaml`: candidate watchlist. Current symbols: `588200.SH`, `159995.SZ`, `159558.SZ`, `159516.SZ`, `588170.SH`, `515880.SH`, `159819.SZ`.
- `config/universes/tech_scan_ai.yaml`: scan universe with 26 symbols across semiconductor/chip/equipment, communication/CPO, AI/cloud, and HK/cross-border tech groups.

Layer semantics:

### operation

- Operation/core means current holdings and a small set of operation-check core records.
- `required_for_operation=true` records can affect strict only in operation/core paths.
- `affect_core_strict=true` belongs only to core operation semantics.
- Adding an operation validator or operation-candidate layer does not make a symbol a purchase target.
- Reference outputs must not override operation strict.

### watchlist

- Watchlist is for same-group relative observation, sector confirmation, QDII comparison, event observation, and candidate follow-up.
- Watchlist remains reference-only.
- It does not directly provide trade prices or instructions.

### candidate

- Candidate means a symbol may be reviewed for future action if data and separate conditions are satisfied.
- Current `tech_operation_candidates` records are reference-only and not operation-grade.
- Candidate is not a default buy list.
- Candidate failure must not block `run_tech_fast_strict.ps1`.

### scan

- Scan is broad coverage and review priority.
- Scan output must not be used directly for trading.
- Scan output must not replace operation output.
- Scan/watchlist/candidate records must not auto-promote to operation or core holdings.

Hard boundaries:

- `159516.SZ` is currently in `tech_core.yaml` and symbol registry notes say it was promoted from operation_candidate into core. Treat any further operation use as core strict governed. Do not treat it as a replenishment candidate by default. It may be reviewed only as failure-trial observation or new-trade reevaluation if a future version explicitly asks for that workflow.
- `002463` was not found in current `config/*.yaml` or `config/universes/*.yaml` during handoff generation. It must not be added to candidate by default. Treat it as event observation only unless the user explicitly authorizes an individual-stock event position workflow.
- QDII premium pool is currently comparison/monitoring only. Guard does not implement complete `premium_pct`, `IOPV`, or `estimated_nav`.
- `GOLD_CNY` is a manual reference/defensive asset price. It does not cover formal gold asset amount or account-level gold valuation by itself.
- No layer may automatically modify config or promote symbols.

## 5. Current Provider / Cache Policy

Provider/cache facts:

- UAT run cache and pipeline run cache currently cache only `akshare.fund_etf_spot_em`.
- UAT cache directory: `outputs_uat_run_cache_latest`.
- Pipeline cache directory: `outputs_tech_pipeline_cache_latest`.
- The cache is opt-in and run-scoped.
- The cache is not global, not permanent, and not reused across UAT/pipeline runs.
- Minute bars are not cached.
- YFinance is not cached.
- Eastmoney Direct is not cached.
- VWAP / intraday metrics are not cached.
- Operation readiness results are not cached.
- Cache hit must not change freshness, stale checks, strict, quote trust tier, usable_for_operation, or operation/reference semantics.
- Cache hit must be reported as cache hit, not as a fresh live provider success.

Provider policy:

- Scan fast: YFinance fallback disabled by default.
- Scan fast: A-share stock scan symbols use Eastmoney Direct reference quote first.
- Minute balanced: YFinance fallback enabled until circuit opens.
- Minute diagnostic: YFinance remains available but protected by circuit.
- Eastmoney Direct and YFinance outputs are reference-only in these paths and must not become operation-grade.

## 6. YFinance Circuit Breaker Current State

Implementation file:

- `src/market_price_guard/yfinance_circuit.py`

Circuit scope:

- `yfinance_circuit_scope=run_only`
- Current script run only.
- Not persisted.
- Not cross-day.
- Not global permanent disable.
- Not a cache.

Trigger conditions:

- One `YFRateLimitError`.
- Error text containing `Too Many Requests`.
- Error text containing `Rate limited`.
- Error text containing `YFRateLimitError`.
- Consecutive YFinance provider timeouts >= 2.
- Current run `yfinance_error_count >= 3`.
- Current run `yfinance_timeout_count >= 3`.

After circuit opens:

- Later YFinance calls in the same run are skipped.
- Records/diagnostics mark `fallback_skipped_yfinance_circuit_open`.
- Runtime diagnostics report:
  - `yfinance_circuit_open`
  - `yfinance_circuit_reason`
  - `yfinance_attempted_count`
  - `yfinance_success_count`
  - `yfinance_error_count`
  - `yfinance_timeout_count`
  - `yfinance_rate_limited_count`
  - `yfinance_skipped_by_circuit_count`
  - `fallback_skipped_yfinance_circuit_open_count`
- Circuit open must not fail the script.
- Circuit open must not change strict.
- Circuit open must not change `usable_for_operation`.
- Circuit open must not change `quote_trust_tier`.

v0.7.3.1 report fixes:

- Scan upload `scan_mode` is populated from runtime.
- Scan `run_time_budget_exceeded` is aligned to runtime diagnostics.
- Minute debug old v0.7.2a wording is replaced.
- `diagnostic_only` is clarified as provider capability label only.

Known coverage caveat:

- Based on code inspection, YFinance circuit affects provider_router base quote attempts and minute fallback attempts. Output verification needs rerun because output directories are absent at handoff generation time.

## 7. Current Known Issues / Backlog

Current unresolved issues and backlog:

- `akshare.fund_etf_spot_em` first call may be slow, e.g. 50s+ in live runs.
- Eastmoney Direct base quote calls are still serial and may be slow.
- `run_tech_minute_probe.ps1` can still exceed the 30s budget, especially when AKShare minute endpoints are slow or unstable.
- `run_tech_scan_ai.ps1` can still exceed the 30s budget on AKShare batch cache miss.
- `MinuteWorkers` is parsed and reported but does not enable true parallel execution; current execution remains serial.
- Full UAT can still be slow.
- QDII Premium Framework is not implemented.
- NDX / QQQ / FX reference framework is not implemented.
- UI Config Manager is not implemented.
- A-share stock, external market, and macro symbol provider aliases require ongoing validation.
- Temporary `fast_no_yfinance` config was not found in current config files during handoff generation. If a user has such a local variant outside the repo, treat it as temporary and not as the official removal of external references.
- Current outputs were not present at handoff generation time; current runtime counts and provider success/failure states are unknown until regenerated.
- README contains some older historical sections for v0.7.2a and earlier. Do not infer current capability solely from older README paragraphs; prefer current scripts, docs/runtime_modes.md, current_provider_chains.md, and source code.

## 8. Strict Safety Rules

Hard safety rules for all future work:

- Do not automatically modify positions.
- Do not add transactions.
- Do not modify cost basis.
- Do not modify gold amount.
- Do not modify the controller 1,000,000 CNY account denominator or total-control convention.
- Do not automatically promote symbols.
- Scan/watchlist/candidate must not auto-promote to operation.
- Reference / minute / VWAP data must not upgrade operation-grade readiness.
- Do not output buy, sell, add, reduce, do-T, order price, target price, `action_hint`, or `preferred_action`.
- Do not implement QDII premium unless a future version explicitly asks for it.
- Do not implement UI unless a future version explicitly asks for it.
- Do not change strict, `usable_for_operation`, or `quote_trust_tier` semantics.
- Do not change operation/reference semantics without explicit version scope.
- Do not make Eastmoney Direct or YFinance operation-grade through scan/minute/reference paths.
- Do not let cache hit override freshness or strict.

## 9. Recommended Next Version

Suggested next version:

`v0.7.3.2 | Provider Runtime Budget Hardening`

Possible goals:

- AKShare ETF batch runtime guard and/or cache warmup.
- Eastmoney Direct base quote runtime optimization.
- Minute probe runtime budget hardening.
- Provider `actual_attempted` vs configured `provider_chain` reporting polish.
- Optional bounded provider attempts.
- Optional true limited concurrency if it can be implemented safely and reported accurately.
- Better per-symbol timeout and skip reporting without changing operation semantics.

Explicitly out of scope for v0.7.3.2 unless the user says otherwise:

- Do not implement QDII premium.
- Do not implement advice layer.
- Do not implement UI.
- Do not change config layer semantics.
- Do not auto-promote symbols.
- Do not make scan/watchlist/candidate operation-grade.

## 10. Suggested Acceptance Commands

Run from repository root:

```powershell
pytest
```

Tech research pipeline:

```powershell
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
echo $LASTEXITCODE
Get-Content outputs_tech_pipeline_latest\pipeline_summary.md -Encoding UTF8
```

Minute balanced:

```powershell
.\scripts\run_tech_minute_probe.ps1 -Mode balanced
echo $LASTEXITCODE
Get-Content outputs_tech_minute_probe_latest\runtime_diagnostics.md -Encoding UTF8
Get-Content outputs_tech_minute_probe_latest\provider_health_report.md -Encoding UTF8
```

UAT:

```powershell
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
echo $LASTEXITCODE

.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
echo $LASTEXITCODE
```

Config diff check:

```powershell
git diff -- config
```

No-trading-advice report scan:

```powershell
Select-String -Path outputs_tech_pipeline_latest\*.md,outputs_tech_scan_ai_latest\*.md,outputs_tech_minute_probe_latest\*.md -Pattern "买入|卖出|加仓|减仓|做T|挂单|目标价|preferred_action|action_hint|buy|sell|add|reduce" -CaseSensitive:$false
```

Note: Some allowed negative safety phrases may contain forbidden action words in Chinese, for example statements saying those actions are not allowed. Review matches manually before treating them as failures.

## 11. Files New Thread Should Read First

Read these first:

- `docs/HANDOFF_v0.7.3.1.md`
- `docs/runtime_modes.md`
- `docs/uat_profiles.md`
- `docs/uat_run_cache.md`
- `docs/current_provider_chains.md`
- `docs/known_issues.md`
- `docs/output_contract.md`
- `config/universes/tech_core.yaml`
- `config/universes/tech_operation_candidates.yaml`
- `config/universes/tech_watchlist.yaml`
- `config/universes/tech_scan_ai.yaml`
- `config/symbol_registry.yaml`
- `scripts/run_tech_research_pipeline.ps1`
- `scripts/run_tech_scan_ai.ps1`
- `scripts/run_tech_minute_probe.ps1`
- `scripts/run_uat.ps1`
- `src/market_price_guard/yfinance_circuit.py`
- `src/market_price_guard/provider_router.py`
- `src/market_price_guard/minute_bars.py`
- `src/market_price_guard/main.py`
- `src/market_price_guard/report.py`

Requested but not found:

- `docs/CONFIG_LAYER_RULES.md`: not found.

Output files to inspect after regeneration:

- `outputs_tech_pipeline_latest/pipeline_summary.md`
- `outputs_tech_scan_ai_latest/0_upload_bundle.md`
- `outputs_tech_scan_ai_latest/runtime_diagnostics.md`
- `outputs_tech_minute_probe_latest/0_upload_bundle.md`
- `outputs_tech_minute_probe_latest/runtime_diagnostics.md`
- `outputs_tech_minute_probe_latest/provider_health_report.md`
- `outputs_tech_intraday_latest/intraday_metrics_snapshot.csv`
- `outputs_uat_summary.md`

At handoff generation time these outputs were not present in the workspace root, so they need to be regenerated.

## 12. Commit / Tag Recommendation

Current committed state already includes:

```text
1fa3261 polish reports and add yfinance circuit breaker
```

Current tag already exists:

```text
v0.7.3.1-report-polish-yfinance-circuit-pass
```

This handoff file itself is new and not included in that commit/tag.

Recommendation after reviewing this handoff file:

```powershell
git add docs/HANDOFF_v0.7.3.1.md
git commit -m "add v0.7.3.1 handoff"
```

No new version tag is required for the handoff-only commit unless the maintainer wants a documentation tag.
