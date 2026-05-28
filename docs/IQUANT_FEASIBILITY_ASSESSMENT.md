# Guosen iQuant Feasibility Assessment

Version: v0.7.5.4

Scope classification: operation data source feasibility matrix and readiness-tier design.

## Confirmed Facts

| fact | status |
|---|---|
| ETF realtime tick support | supported inside iQuant |
| ETF level-5 quote depth support | supported inside iQuant |
| 00883.HK realtime quote support | supported inside iQuant |
| Python API external call from market_price_guard | not available under current broker response |
| strategy authoring and runtime | must stay inside iQuant |
| local JSON / CSV file output from strategy | not allowed under current broker response |
| automated market_price_guard provider eligibility | not eligible now |
| current recommended role | manual_verification_source / internal_strategy_platform_candidate |
| provider_router entry | no |
| operation_primary role | no |

## Conclusion

Guosen iQuant has strong internal quote capability but is not currently eligible as an automated market_price_guard provider because it is neither externally callable nor bridgeable under the broker's current response.

## Current Position

iQuant can be useful as a manual verification source because it supports strong internal quote views, including ETF realtime ticks, ETF level-5 quote depth, and 00883.HK realtime quote checks.

iQuant can also remain an internal_strategy_platform_candidate for work that runs entirely inside the broker platform.

It must not enter provider_router in v0.7.5.4. It must not be labeled operation_primary. It must not be treated as an automated provider unless a future broker response confirms an external or bridge export path.

## Remaining Broker Questions

| question | purpose |
|---|---|
| Is an internal strategy allowed to push HTTP POST or socket messages to localhost? | verify bridgeability |
| Does Guosen provide any external quote API, SDK, DLL, or local port service outside iQuant? | verify external callable path |

No trading advice generated. This assessment is data source feasibility only.
