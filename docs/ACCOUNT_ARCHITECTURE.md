# market_price_guard Account Architecture

## 1. Project Scope

market_price_guard is not tech-only.
It must gradually support multiple independent investment execution accounts.

Current required accounts:
- tech
- energy

Future summary layer:
- controller / portfolio summary

## 2. Account Isolation

tech and energy must keep separate:

- layer configs
- operation pools
- operation candidates
- watchlists
- scans
- pipelines
- outputs
- UAT checks
- handoff files
- account-specific rules

## 3. Layer Model

Each account should support:

- operation
- operation_candidate
- watchlist
- scan

## 4. Scope Classification Before Every Version

Before implementing any future version, classify the version as:

- tech-only
- energy-only
- account-generic
- controller-summary

## 5. Generic-First Rule

Reusable infrastructure should be account-generic unless there is a clear reason not to.

Examples of reusable infrastructure:
- config source verification
- layer manifest
- config manager CLI
- pipeline runner
- UAT
- upload bundle
- provider runtime budget
- report generation
- handoff generation

## 6. Tech-only Debt Rule

If a version is implemented as tech-only, it must record:

- why tech-only is acceptable now
- which files/functions/scripts are tech-only
- future energy adaptation cost
- whether account abstraction is deferred

## 7. Strict Prohibitions

- Do not mix tech and energy holdings.
- Do not apply tech-specific strategy rules to energy by default.
- Do not let controller replace account execution.
- Do not output trading advice unless explicitly requested inside the proper account context.
- Do not change account positions, cost basis, cash, gold amount, or total-control assets from config tools.

## 8. Handoff Requirement

Every future HANDOFF must include:

- scope classification
- account impact
- tech status
- energy status
- controller status if relevant
- tech-only debt
- future energy adaptation cost
- next thread read list
