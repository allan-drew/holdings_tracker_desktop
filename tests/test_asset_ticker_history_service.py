from datetime import date

import pytest

from holdings_tracker_desktop.models import Asset
from holdings_tracker_desktop.schemas.asset_ticker_history import AssetTickerHistoryCreate
from holdings_tracker_desktop.services.asset_ticker_history_service import AssetTickerHistoryService
from holdings_tracker_desktop.utils.exceptions import ConflictException


def change_ticker(db, asset, new_ticker, day):
    response = AssetTickerHistoryService(db).create(
        AssetTickerHistoryCreate(asset_id=asset.id, new_ticker=new_ticker, change_date=day)
    )
    db.commit()
    return response


def test_ticker_change_to_an_existing_ticker_is_rejected(db, make_asset):
    make_asset("TAKEN3")
    asset = make_asset("OLD3")

    with pytest.raises(ConflictException):
        change_ticker(db, asset, "taken3", date(2024, 1, 1))

    assert db.get(Asset, asset.id).ticker == "OLD3"


def test_deleting_latest_change_restores_previous_ticker(db, make_asset):
    asset = make_asset("OLD3")
    change_ticker(db, asset, "MID3", date(2024, 1, 1))
    latest = change_ticker(db, asset, "NEW3", date(2025, 1, 1))

    AssetTickerHistoryService(db).delete(latest.id)

    assert db.get(Asset, asset.id).ticker == "MID3"


def test_deleting_an_older_change_is_rejected(db, make_asset):
    asset = make_asset("OLD3")
    first = change_ticker(db, asset, "MID3", date(2024, 1, 1))
    change_ticker(db, asset, "NEW3", date(2025, 1, 1))

    with pytest.raises(ConflictException):
        AssetTickerHistoryService(db).delete(first.id)

    assert db.get(Asset, asset.id).ticker == "NEW3"
