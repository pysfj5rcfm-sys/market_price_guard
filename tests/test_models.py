import pytest
from pydantic import ValidationError

from market_price_guard.models import RawPrice, Watchlist


def test_raw_price_rejects_negative_price():
    with pytest.raises(ValidationError):
        RawPrice(symbol="BAD", price=-1, currency="CNY", source="mock")


def test_watchlist_model_accepts_project_structure():
    watchlist = Watchlist.model_validate(
        {
            "projects": {
                "energy": {
                    "display_name": "理财｜能源账户项目",
                    "allow_full_detail": True,
                    "instruments": [
                        {
                            "symbol": "00883.HK",
                            "name": "中海油H",
                            "market": "HK",
                            "core": True,
                            "provider": "mock",
                        }
                    ],
                }
            }
        }
    )

    assert watchlist.projects["energy"].instruments[0].symbol == "00883.HK"
