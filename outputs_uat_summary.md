# market_price_guard UAT Summary

- generated_at: 2026-05-18T14:06:27.2673189Z
- total: 5
- passed: 5
- strict_blocked_but_reported: 0
- failed: 0

strict=2 means the price guard blocked operation; it is not a UAT failure when reports are generated and blocking is explained.

## Items

### tech_fast_strict
- command/script: run_tech_fast_strict.ps1
- exit_code: 0
- status: passed
- output_dir: outputs_tech_latest
- index.md exists: True
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### energy_fast_strict
- command/script: run_energy_fast_strict.ps1
- exit_code: 0
- status: passed
- output_dir: outputs_energy_latest
- index.md exists: True
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### all_fast_strict
- command/script: run_all_fast_strict.ps1
- exit_code: 0
- status: passed
- output_dir: outputs_all_latest
- index.md exists: True
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### diagnostic
- command/script: run_diagnostic.ps1
- exit_code: 0
- status: passed
- output_dir: outputs_diagnostic
- index.md exists: True
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.

### mock_strict
- command/script: run_mock_strict.ps1
- exit_code: 0
- status: passed
- output_dir: outputs_mock_latest
- index.md exists: True
- data_completeness_report.md exists: True
- provider_health_report.md exists: True
- runtime_diagnostics.md exists: True
- price_block exists: True
- missing_files: none
- advice_keyword_hits: none
- notes: strict_blocked_but_reported is acceptable when blocking reports exist.
