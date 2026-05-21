# market_price_guard Current Provider Chains

Provider chain and field capability are separate layers. A provider can supply a valid price without validated bid/ask, turnover, minute bars, or QDII premium fields. A field being present also does not imply operation-grade permission; operation boundaries still use `quote_trust_tier`, `usable_for_operation`, strict, and freshness.

v0.7.1.6 adds `config/provider_capabilities.yaml` and `provider_capability_report.md` for field support, unit confidence, and comparability diagnostics. This does not change any provider chain.

## Tech Operation Fast

Script: `.\scripts\run_tech_fast_strict.ps1`

Output: `outputs_tech_latest/`

- `quote_purpose=operation`
- This is the operation / strict path.
- It is not changed into a reference path by Eastmoney Direct or yfinance.
- Eastmoney Direct is not operation-grade and cannot by itself pass operation strict.

## Tech Reference Fast

Script: `.\scripts\run_tech_fast_reference.ps1`

Output: `outputs_tech_reference_latest/`

- `quote_purpose=reference`
- Fast reference path.
- Effective ETF chain: `eastmoney_direct -> yfinance -> akshare -> mock`.
- Slow AKShare may be skipped for speed.
- Not usable for concrete operation advice.

## Tech Reconcile

Script: `.\scripts\run_tech_reconcile.ps1`

Output: `outputs_tech_reconcile_latest/`

- `quote_purpose=reference`
- `reconcile_mode=full`
- Tries Eastmoney Direct, yfinance, and AKShare for multi-source quality diagnostics.
- Not usable for concrete operation advice.
- Does not change operation strict.

## Tech Operation Candidates

Script: `.\scripts\run_tech_operation_candidates.ps1`

Output: `outputs_tech_operation_candidates_latest/`

- `quote_purpose=reference`
- Universe: `tech_operation_candidates`
- This is a pre-trade verification layer for symbols manually selected from scan or watchlist outputs.
- It is not core holdings and is not operation-grade.
- Candidate records keep `required_for_operation=false`, `usable_for_operation=false`, and `affect_core_strict=false`.
- Failures in this universe do not affect `run_tech_fast_strict.ps1` or `outputs_tech_latest`.

## Energy Fast Strict

Script: `.\scripts\run_energy_fast_strict.ps1`

Output: `outputs_energy_latest/`

- `quote_purpose=operation`
- Covers `00883.HK`, `601899.SH`, `601985.SH`, and `003816.SZ`.
- Eastmoney Direct is not forced for `00883.HK`.
- A-share energy reconciliation may be expanded later, but this path does not change operation strict.

## All / Controller Fast Strict

Script: `.\scripts\run_all_fast_strict.ps1`

Output: `outputs_all_latest/`

- Controller summary path.
- Does not emit `energy_price_block.md` or `tech_price_block.md`.
- Does not replace the energy or tech project operation paths.

## Diagnostic

Script: `.\scripts\run_diagnostic.ps1`

Output: `outputs_diagnostic/`

- Troubleshooting path.
- May try multiple providers.
- Does not change operation selected-provider judgment.

## Upload Rule

Daily upload starts with `0_upload_bundle.md`.

Add `debug_bundle.md` only when the upload bundle shows strict blocking, provider errors, stale prices, quote_time issues, major reconciliation differences, runtime budget issues, or other contradictions.

## Universe Layer

`config/symbol_registry.yaml` supplies symbol metadata. `config/universes/*.yaml` selects the current run universe.

- `core_holdings`: may contain `required_for_operation=true` records and may affect strict.
- `candidate_watchlist`: reference/conditional candidates; does not affect core strict.
- `scan_universe`: reference scan pool; does not affect core strict.
- `operation_candidate`: reference-only pre-trade verification candidates; does not affect core strict.

Provider chains can vary by `quote_purpose` and universe metadata, but candidate, operation-candidate, and scan records remain non-strict until explicitly promoted to `core_holdings`.

## Field Capability Matrix

`docs/api_field_capability_matrix.md` tracks provider field support separately from provider chain selection.

A provider being selected for price does not mean it supports minute bars, IOPV, bid/ask, or every scan field. Likewise, a field being supported does not make a record operation-grade; operation use still depends on `quote_trust_tier`, `usable_for_operation`, strict, freshness, and provider health.
## Optional Minute Bars Probe

v0.7.2a adds `--include-minute-bars` and `scripts/run_tech_minute_probe.ps1`.

The minute-bars probe is optional. It does not alter the default fast strict provider chain, does not upgrade reference providers, and does not change strict, freshness, quote trust tier, or usable_for_operation.

When the probe is enabled, reports show minute-bar availability, interval, count, latest time, provider, status, validation status, and missing reason. VWAP and intraday derived fields are not calculated in v0.7.2a.

## v0.7.2a.1 Scan And Minute Probe Coverage

`tech_scan_ai` reference/scan runs may attempt AKShare spot quotes for ETF / QDII ETF scan candidates and A-share stock scan candidates. These records remain scan/reference records and do not become operation holdings.

The optional minute probe may call AKShare `fund_etf_hist_min_em` for ETF / QDII ETF symbols. This does not alter `run_tech_fast_strict.ps1`, default provider chains, strict, or operation readiness.

v0.7.2a.2b minute probe order:

1. AKShare ETF minute probe.
2. Eastmoney Direct minute probe fallback.
3. YFinance reference minute fallback.

Eastmoney Direct and YFinance minute bars do not alter the default fast strict provider chain and do not upgrade operation readiness.

## Reference Intraday Metrics

Script: `.\scripts\run_tech_intraday_metrics.ps1`

Output: `outputs_tech_intraday_latest/`

- Reads existing minute probe and spot CSV artifacts.
- Covers `tech_core` and `tech_operation_candidates` from universe config.
- Computes reference VWAP and basic intraday position metrics only.
- Uses minute source priority metadata: AKShare, Eastmoney Direct, then YFinance fallback.
- Does not call providers and does not alter the default fast strict provider chain.
- Does not change strict, quote trust tier, freshness, usable_for_operation, or operation/reference semantics.
