# market_price_guard UAT Summary

- generated_at: 2026-05-21T07:13:27.2673229Z
- mode: full
- profile_explanation: full mode runs the complete live provider regression and can be slow.
- use_run_cache: true
- run_cache_dir: D:\AIProjects\market_price_guard\outputs_uat_run_cache_latest
- cache_scope: uat_run
- cache_enabled_functions: akshare.fund_etf_spot_em
- cache_hit_count: 8
- cache_miss_count: 1
- cache_bypass_count: 0
- cache_error_count: 0
- estimated_cache_saved_calls: 8
- estimated_cache_saved_seconds: provider-dependent
- total_defined: 12
- run_count: 12
- passed: 9
- strict_blocked_but_reported: 3
- failed: 0
- skipped_by_profile: 0
- total: 12

strict=2 means the price guard blocked operation; it is not a UAT failure when reports are generated and blocking is explained.
skipped_by_profile means the item is intentionally skipped by the selected UAT mode and is not a failure.

## Slowest Items

| item | elapsed_seconds | status |
|---|---:|---|
| diagnostic | 122.726 | passed |
| tech_scan_ai | 93.979 | passed |
| tech_fast_strict | 25.251 | passed |
| tech_minute_probe | 20.496 | passed |
| tech_reconcile | 12.916 | passed |

## Items

### tech_fast_strict
- command/script: run_tech_fast_strict.ps1
- exit_code: 0
- status: passed
- mode: full
- elapsed_seconds: 25.251
- cache_hits: 8
- cache_misses: 1
- cache_bypass: 0
- cache_note: UAT run cache summary is run-level; provider attempts show per-script hit/miss where available.
- output_dir: outputs_tech_latest
- index.md exists: True
- 0_upload_bundle.md exists: True
- debug_bundle.md exists: True
- quote_purpose: operation
- universe_type: 
- unsupported_count: 0
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_reconciliation_report.md exists: True
- unsupported_symbols_report.md exists: False
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### tech_fast_reference
- command/script: run_tech_fast_reference.ps1
- exit_code: 0
- status: passed
- mode: full
- elapsed_seconds: 11.533
- cache_hits: 8
- cache_misses: 1
- cache_bypass: 0
- cache_note: UAT run cache summary is run-level; provider attempts show per-script hit/miss where available.
- output_dir: outputs_tech_reference_latest
- index.md exists: True
- 0_upload_bundle.md exists: True
- debug_bundle.md exists: True
- quote_purpose: reference
- universe_type: 
- unsupported_count: 0
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_reconciliation_report.md exists: True
- unsupported_symbols_report.md exists: False
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### tech_reconcile
- command/script: run_tech_reconcile.ps1
- exit_code: 0
- status: passed
- mode: full
- elapsed_seconds: 12.916
- cache_hits: 8
- cache_misses: 1
- cache_bypass: 0
- cache_note: UAT run cache summary is run-level; provider attempts show per-script hit/miss where available.
- output_dir: outputs_tech_reconcile_latest
- index.md exists: True
- 0_upload_bundle.md exists: True
- debug_bundle.md exists: True
- quote_purpose: reference
- universe_type: 
- unsupported_count: 0
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_reconciliation_report.md exists: True
- unsupported_symbols_report.md exists: False
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### tech_watchlist
- command/script: run_tech_watchlist.ps1
- exit_code: 0
- status: passed
- mode: full
- elapsed_seconds: 6.892
- cache_hits: 8
- cache_misses: 1
- cache_bypass: 0
- cache_note: UAT run cache summary is run-level; provider attempts show per-script hit/miss where available.
- output_dir: outputs_tech_watchlist_latest
- index.md exists: True
- 0_upload_bundle.md exists: True
- debug_bundle.md exists: True
- quote_purpose: reference
- universe_type: candidate_watchlist
- unsupported_count: 0
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_reconciliation_report.md exists: True
- unsupported_symbols_report.md exists: False
- price_block exists: True
- strict_pollution_isolation: candidate/scan/operation-candidate universes are non-strict reference outputs.
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### tech_scan_ai
- command/script: run_tech_scan_ai.ps1
- exit_code: 0
- status: passed
- mode: full
- elapsed_seconds: 93.979
- cache_hits: 8
- cache_misses: 1
- cache_bypass: 0
- cache_note: UAT run cache summary is run-level; provider attempts show per-script hit/miss where available.
- output_dir: outputs_tech_scan_ai_latest
- index.md exists: True
- 0_upload_bundle.md exists: True
- debug_bundle.md exists: True
- quote_purpose: reference
- universe_type: scan_universe
- unsupported_count: 0
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_reconciliation_report.md exists: True
- unsupported_symbols_report.md exists: False
- price_block exists: True
- strict_pollution_isolation: candidate/scan/operation-candidate universes are non-strict reference outputs.
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### tech_operation_candidates
- command/script: run_tech_operation_candidates.ps1
- exit_code: 0
- status: passed
- mode: full
- elapsed_seconds: 1.878
- cache_hits: 8
- cache_misses: 1
- cache_bypass: 0
- cache_note: UAT run cache summary is run-level; provider attempts show per-script hit/miss where available.
- output_dir: outputs_tech_operation_candidates_latest
- index.md exists: True
- 0_upload_bundle.md exists: True
- debug_bundle.md exists: True
- quote_purpose: reference
- universe_type: operation_candidate
- unsupported_count: 0
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_reconciliation_report.md exists: True
- unsupported_symbols_report.md exists: False
- price_block exists: True
- strict_pollution_isolation: candidate/scan/operation-candidate universes are non-strict reference outputs.
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### tech_minute_probe
- command/script: run_tech_minute_probe.ps1
- exit_code: 0
- status: passed
- mode: full
- elapsed_seconds: 20.496
- cache_hits: 8
- cache_misses: 1
- cache_bypass: 0
- cache_note: UAT run cache summary is run-level; provider attempts show per-script hit/miss where available.
- output_dir: outputs_tech_minute_probe_latest
- index.md exists: True
- 0_upload_bundle.md exists: True
- debug_bundle.md exists: True
- quote_purpose: reference
- universe_type: minute_probe
- unsupported_count: 0
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_reconciliation_report.md exists: True
- unsupported_symbols_report.md exists: False
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### tech_intraday_metrics
- command/script: run_tech_intraday_metrics.ps1
- exit_code: 0
- status: passed
- mode: full
- elapsed_seconds: 1.477
- cache_hits: 8
- cache_misses: 1
- cache_bypass: 0
- cache_note: UAT run cache summary is run-level; provider attempts show per-script hit/miss where available.
- output_dir: outputs_tech_intraday_latest
- index.md exists: True
- 0_upload_bundle.md exists: True
- debug_bundle.md exists: True
- quote_purpose: 
- universe_type: 
- unsupported_count: 0
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_reconciliation_report.md exists: True
- unsupported_symbols_report.md exists: False
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### energy_fast_strict
- command/script: run_energy_fast_strict.ps1
- exit_code: 2
- status: strict_blocked_but_reported
- mode: full
- elapsed_seconds: 9.799
- cache_hits: 8
- cache_misses: 1
- cache_bypass: 0
- cache_note: UAT run cache summary is run-level; provider attempts show per-script hit/miss where available.
- output_dir: outputs_energy_latest
- index.md exists: True
- 0_upload_bundle.md exists: True
- debug_bundle.md exists: True
- quote_purpose: operation
- universe_type: 
- unsupported_count: 0
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_reconciliation_report.md exists: True
- unsupported_symbols_report.md exists: False
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### all_fast_strict
- command/script: run_all_fast_strict.ps1
- exit_code: 2
- status: strict_blocked_but_reported
- mode: full
- elapsed_seconds: 9.587
- cache_hits: 8
- cache_misses: 1
- cache_bypass: 0
- cache_note: UAT run cache summary is run-level; provider attempts show per-script hit/miss where available.
- output_dir: outputs_all_latest
- index.md exists: True
- 0_upload_bundle.md exists: True
- debug_bundle.md exists: True
- quote_purpose: operation
- universe_type: 
- unsupported_count: 0
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_reconciliation_report.md exists: True
- unsupported_symbols_report.md exists: False
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### diagnostic
- command/script: run_diagnostic.ps1
- exit_code: 0
- status: passed
- mode: full
- elapsed_seconds: 122.726
- cache_hits: 8
- cache_misses: 1
- cache_bypass: 0
- cache_note: UAT run cache summary is run-level; provider attempts show per-script hit/miss where available.
- output_dir: outputs_diagnostic
- index.md exists: True
- 0_upload_bundle.md exists: True
- debug_bundle.md exists: True
- quote_purpose: operation
- universe_type: 
- unsupported_count: 0
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_reconciliation_report.md exists: True
- unsupported_symbols_report.md exists: False
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### mock_strict
- command/script: run_mock_strict.ps1
- exit_code: 2
- status: strict_blocked_but_reported
- mode: full
- elapsed_seconds: 1.415
- cache_hits: 8
- cache_misses: 1
- cache_bypass: 0
- cache_note: UAT run cache summary is run-level; provider attempts show per-script hit/miss where available.
- output_dir: outputs_mock_latest
- index.md exists: True
- 0_upload_bundle.md exists: True
- debug_bundle.md exists: True
- quote_purpose: operation
- universe_type: 
- unsupported_count: 0
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_reconciliation_report.md exists: True
- unsupported_symbols_report.md exists: False
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.
