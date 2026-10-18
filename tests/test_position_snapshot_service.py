from datetime import date
from decimal import Decimal

import pytest

from holdings_tracker_desktop.models import BrokerNote, PositionSnapshot
from holdings_tracker_desktop.models.asset_event import AssetEventType
from holdings_tracker_desktop.models.broker_note import OperationType
from holdings_tracker_desktop.schemas.asset_event import AssetEventCreate
from holdings_tracker_desktop.schemas.broker_note import BrokerNoteCreate, BrokerNoteUpdate
from holdings_tracker_desktop.services.asset_event_service import AssetEventService
from holdings_tracker_desktop.services.broker_note_service import BrokerNoteService
from holdings_tracker_desktop.utils.exceptions import ValidationException


def add_note(db, refs, asset, operation, day, quantity, price="10"):
    return BrokerNoteService(db).create(
        BrokerNoteCreate(
            date=day,
            operation=operation,
            broker_id=refs["broker"].id,
            asset_id=asset.id,
            quantity=Decimal(quantity),
            price=Decimal(price),
        )
    )


def add_event(db, asset, event_type, day, **fields):
    return AssetEventService(db).create(
        AssetEventCreate(asset_id=asset.id, event_type=event_type, date=day, **fields)
    )


def last_snapshot(db, asset):
    return (
        db.query(PositionSnapshot)
        .filter(PositionSnapshot.asset_id == asset.id)
        .order_by(PositionSnapshot.snapshot_date.desc(), PositionSnapshot.id.desc())
        .first()
    )


def test_split_multiplies_quantity_and_keeps_cost(db, refs, make_asset):
    asset = make_asset("AAAA3")
    add_note(db, refs, asset, OperationType.BUY, date(2024, 1, 10), "100", "50")

    add_event(db, asset, AssetEventType.SPLIT, date(2024, 2, 1), factor=Decimal("0.1"))

    snapshot = last_snapshot(db, asset)
    assert snapshot.quantity == Decimal("1000")
    assert snapshot.total_cost == Decimal("5000")


def test_reverse_split_divides_quantity(db, refs, make_asset):
    asset = make_asset("BBBB3")
    add_note(db, refs, asset, OperationType.BUY, date(2024, 1, 10), "1000", "1")

    add_event(db, asset, AssetEventType.REVERSE_SPLIT, date(2024, 2, 1), factor=Decimal("10"))

    snapshot = last_snapshot(db, asset)
    assert snapshot.quantity == Decimal("100")
    assert snapshot.avg_price == Decimal("10")


def test_same_day_sell_registered_before_buy_is_applied(db, refs, make_asset):
    asset = make_asset("CCCC3")
    add_note(db, refs, asset, OperationType.BUY, date(2024, 1, 1), "100")
    day = date(2024, 3, 5)

    # Day trade: SELL is registered before the BUY of the same day.
    service = BrokerNoteService(db)
    sell = add_note(db, refs, asset, OperationType.SELL, day, "100")
    add_note(db, refs, asset, OperationType.BUY, day, "50")

    # Editing the earlier note rebuilds the whole same-day timeline.
    service.update(sell.id, BrokerNoteUpdate(quantity=Decimal("120")))

    assert last_snapshot(db, asset).quantity == Decimal("30")


def test_sell_above_position_is_rejected_and_nothing_is_saved(db, refs, make_asset):
    asset = make_asset("DDDD3")
    add_note(db, refs, asset, OperationType.BUY, date(2024, 1, 1), "100")
    snapshots_before = db.query(PositionSnapshot).count()

    with pytest.raises(ValidationException):
        add_note(db, refs, asset, OperationType.SELL, date(2024, 2, 1), "150")

    assert db.query(BrokerNote).count() == 1
    assert db.query(PositionSnapshot).count() == snapshots_before
    assert last_snapshot(db, asset).quantity == Decimal("100")


def test_deleting_buy_that_backs_a_later_sell_is_rejected(db, refs, make_asset):
    asset = make_asset("EEEE3")
    buy = add_note(db, refs, asset, OperationType.BUY, date(2024, 1, 1), "100")
    add_note(db, refs, asset, OperationType.SELL, date(2024, 2, 1), "40")

    with pytest.raises(ValidationException):
        BrokerNoteService(db).delete(buy.id)

    assert db.query(BrokerNote).count() == 2
    assert last_snapshot(db, asset).quantity == Decimal("60")


def test_total_conversion_moves_position_to_target(db, refs, make_asset):
    source = make_asset("FFFF3")
    target = make_asset("GGGG3")
    add_note(db, refs, source, OperationType.BUY, date(2024, 1, 1), "100")

    add_event(
        db, source, AssetEventType.TOTAL_CONVERSION, date(2024, 6, 1),
        target_asset_id=target.id,
        target_quantity=Decimal("50"),
        target_unit_price=Decimal("20"),
    )

    assert last_snapshot(db, source).quantity == Decimal("0")
    assert last_snapshot(db, target).quantity == Decimal("50")
    assert last_snapshot(db, target).total_cost == Decimal("1000")


def test_total_value_adds_costs_on_buy_and_deducts_them_on_sell():
    buy = BrokerNote(operation=OperationType.BUY, quantity=Decimal("10"), price=Decimal("5"),
                     fees=Decimal("1"), taxes=Decimal("0.5"))
    sell = BrokerNote(operation=OperationType.SELL, quantity=Decimal("10"), price=Decimal("5"),
                      fees=Decimal("1"), taxes=Decimal("0.5"))

    assert buy.total_value == Decimal("51.5")
    assert sell.total_value == Decimal("48.5")


def test_allocation_is_filtered_by_currency(db, refs, make_asset):
    from holdings_tracker_desktop.models import Asset, Currency
    from holdings_tracker_desktop.services.position_snapshot_service import PositionSnapshotService

    usd = Currency(name="Dollar", code="USD", symbol="US$")
    db.add(usd)
    db.commit()

    brl_asset = make_asset("BRL3")
    usd_asset = Asset(ticker="USD1", type_id=refs["asset_type"].id, currency_id=usd.id)
    db.add(usd_asset)
    db.commit()

    add_note(db, refs, brl_asset, OperationType.BUY, date(2024, 1, 1), "10", "10")
    add_note(db, refs, usd_asset, OperationType.BUY, date(2024, 1, 1), "10", "20")

    service = PositionSnapshotService(db)
    by_brl = service.get_allocation_by_asset(2024, currency_id=refs["currency"].id)
    by_usd = service.get_allocation_by_sector(2024, currency_id=usd.id)

    assert by_brl == [{"label": "BRL3", "value": 100.0}]
    # Assets without a sector get a None label, which the UI translates
    assert by_usd == [{"label": None, "value": 200.0}]


def test_yearly_positions_hide_closed_positions(db, refs, make_asset):
    from holdings_tracker_desktop.services.position_snapshot_service import PositionSnapshotService

    held = make_asset("HELD3")
    closed = make_asset("SOLD3")
    add_note(db, refs, held, OperationType.BUY, date(2024, 1, 1), "10")
    add_note(db, refs, closed, OperationType.BUY, date(2024, 1, 1), "10")
    add_note(db, refs, closed, OperationType.SELL, date(2024, 6, 1), "10")

    tickers = [p["asset_ticker"] for p in PositionSnapshotService(db).list_all_for_ui_by_year(2024)]

    assert tickers == ["HELD3"]
