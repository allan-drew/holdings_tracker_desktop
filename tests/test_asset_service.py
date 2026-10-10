from datetime import date
from decimal import Decimal

import pytest

from holdings_tracker_desktop.models import Asset
from holdings_tracker_desktop.models.asset_event import AssetEventType
from holdings_tracker_desktop.schemas.asset_event import AssetEventCreate
from holdings_tracker_desktop.services.asset_event_service import AssetEventService
from holdings_tracker_desktop.services.asset_service import AssetService
from holdings_tracker_desktop.utils.exceptions import ConflictException


@pytest.fixture
def conversion(db, make_asset):
    source = make_asset("SRC3")
    target = make_asset("TGT3")
    AssetEventService(db).create(
        AssetEventCreate(
            asset_id=source.id,
            event_type=AssetEventType.TOTAL_CONVERSION,
            date=date(2024, 1, 1),
            target_asset_id=target.id,
            target_quantity=Decimal("10"),
            target_unit_price=Decimal("5"),
        )
    )
    return source, target


@pytest.mark.parametrize("side", [0, 1])
def test_asset_in_a_conversion_cannot_be_deleted(db, conversion, side):
    asset = conversion[side]

    with pytest.raises(ConflictException):
        AssetService(db).delete(asset.id)

    assert db.get(Asset, asset.id) is not None


def test_asset_with_only_non_conversion_events_can_be_deleted(db, make_asset):
    asset = make_asset("SPL3")
    AssetEventService(db).create(
        AssetEventCreate(
            asset_id=asset.id,
            event_type=AssetEventType.SPLIT,
            date=date(2024, 1, 1),
            factor=Decimal("0.5"),
        )
    )

    assert AssetService(db).delete(asset.id) is True


def test_app_engine_enforces_sqlite_foreign_keys():
    from holdings_tracker_desktop.database.database import engine

    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
