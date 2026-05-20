# Symbol Registry + Universe Layer

`config/symbol_registry.yaml` is the single place to register symbols. A registry entry describes metadata and routing preferences; it does not make a symbol operation-grade by itself.

## Registry Fields

- `symbol`: internal symbol, such as `159819.SZ`
- `name`: display name
- `market`: `SH`, `SZ`, `HK`, `MANUAL`, `FX`, `US`
- `asset_type`: `ETF`, `stock`, `manual_price`, `fx`, `index`, or `unknown`
- `project_scope`: `tech`, `energy`, or `controller`
- `role`: stable classification, such as `ai_tech_equity`
- `universe_tags`: tags for filtering or scan pools
- `required_for_operation`: only core holdings should set this to true
- `default_quote_purpose`: `operation` or `reference`
- `provider_preference`: provider chains for `operation`, `reference`, and `reconcile`
- `report_group`: human-facing report group
- `enabled`: whether the registry entry is active
- `notes`: validation or business notes

## Universe Files

Universe files live in `config/universes/`. Each file has:

- `name`
- `profile`
- `universe_type`: `core_holdings`, `candidate_watchlist`, `scan_universe`, or `controller_summary`
- `quote_purpose`
- `symbols`

## Strict Isolation

`core_holdings` can affect operation strict when `required_for_operation=true`.

`candidate_watchlist`, `scan_universe`, and unregistered symbols default to `required_for_operation=false`. Provider errors, stale prices, and missing quote times in these universes do not block core operation strict.

## Add A Candidate ETF

1. Add the symbol to `config/symbol_registry.yaml`.
2. Set `required_for_operation: false`.
3. Set `default_quote_purpose: reference`.
4. Add the symbol to a universe such as `config/universes/tech_watchlist.yaml`.
5. Run `.\scripts\run_tech_watchlist.ps1`.

## Add An AI Scan Pool Symbol

Add the symbol to the registry, tag it with `tech`, `ai` or the relevant theme, then include it in `config/universes/tech_scan_ai.yaml`.

## Unsupported Symbols

Temporary symbols passed by `--symbols` or `--symbol-file` that are not in the registry are treated as scan-only records. They appear in `unsupported_symbols_report.md` and never affect core strict.
