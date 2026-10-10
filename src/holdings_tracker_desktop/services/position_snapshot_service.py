from datetime import date as Date
from decimal import Decimal
from typing import List

from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from holdings_tracker_desktop.models import Asset, AssetEvent, AssetSector, BrokerNote, PositionSnapshot
from holdings_tracker_desktop.models.asset_event import AssetEventType
from holdings_tracker_desktop.models.broker_note import OperationType
from holdings_tracker_desktop.repositories.base_repository import BaseRepository
from holdings_tracker_desktop.schemas.position_snapshot import (
  PositionSnapshotCreate, PositionSnapshotUpdate, PositionSnapshotResponse
)
from holdings_tracker_desktop.utils.exceptions import ValidationException

# Tolerance for quantities stored as Numeric(20, 6)
QUANTITY_TOLERANCE = Decimal("0.000001")

class PositionSnapshotService:
    def __init__(self, db: Session):
        self.repository = BaseRepository[PositionSnapshot, PositionSnapshotCreate, PositionSnapshotUpdate](
            model=PositionSnapshot,
            db=db
        )
        self.db = db

    def create(self, data: PositionSnapshotCreate) -> PositionSnapshotResponse:
        """Create new PositionSnapshot with validation"""
        position_snapshot = self.repository.create_from_schema(data)
        return PositionSnapshotResponse.model_validate(position_snapshot)

    def get(self, position_snapshot_id: int) -> PositionSnapshotResponse:
        """Get PositionSnapshot by ID"""
        position_snapshot = self.repository.get_or_raise(position_snapshot_id)
        return PositionSnapshotResponse.model_validate(position_snapshot)

    def list_all_for_ui_by_asset(
        self,
        asset_id: int,
        skip: int = 0,
        limit: int | None = None
    ) -> List[dict]:
        """Get PositionSnapshots already formatted for UI"""
        snapshots = (
            self.db.query(PositionSnapshot)
            .filter(PositionSnapshot.asset_id == asset_id)
            .order_by(
                PositionSnapshot.snapshot_date.desc(),
                PositionSnapshot.id.desc()
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

        return [s.to_ui_dict() for s in snapshots]

    def list_all_for_ui_by_year(
        self,
        year: int,
        asset_type_id: int | None = None,
        skip: int = 0,
        limit: int | None = None
    ) -> List[dict]:
        """Get PositionSnapshots already formatted for UI, optionally filtered by asset type"""
        subquery = (
            self.db.query(
                PositionSnapshot.asset_id,
                func.max(PositionSnapshot.snapshot_date).label("max_date"),
                func.max(PositionSnapshot.id).label("max_id")
            )
            .filter(func.extract("year", PositionSnapshot.snapshot_date) <= year)
            .group_by(PositionSnapshot.asset_id)
            .subquery()
        )

        snapshots = (
            self.db.query(PositionSnapshot)
            .join(
                subquery,
                (PositionSnapshot.asset_id == subquery.c.asset_id) &
                (PositionSnapshot.id == subquery.c.max_id)
            )
            .join(Asset, Asset.id == PositionSnapshot.asset_id)
        )

        if asset_type_id is not None:
            snapshots = snapshots.filter(Asset.type_id == asset_type_id)

        snapshots = (
            snapshots
            .order_by(Asset.ticker.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return [s.to_ui_dict() for s in snapshots]

    def count_all(self) -> int:
        """Count all PositionSnapshots"""
        return self.repository.count()

    def get_earliest_snapshot_date(self) -> Date | None:
        min_date: Date | None = self.db.query(func.min(PositionSnapshot.snapshot_date)).scalar()
        return min_date

    def get_allocation_by_asset(self, year: int, asset_type_id: int | None = None) -> list[dict]:
        query, total_cost = self._base_allocation_query(year)

        query = query.with_entities(
            Asset.ticker, 
            total_cost
        )

        if asset_type_id is not None:
            query = query.filter(Asset.type_id == asset_type_id)

        rows = (
            query
            .group_by(Asset.ticker)
            .order_by(total_cost.desc())
            .all()
        )

        return [
            {"label": ticker, "value": float(total)}
            for ticker, total in rows
            if total > 0
        ]

    def get_allocation_by_sector(self, year: int, asset_type_id: int | None = None) -> list[dict]:
        query, total_cost = self._base_allocation_query(year)

        sector_label = func.coalesce(AssetSector.name, "Unclassified").label("sector_name")

        query = query.with_entities(
            sector_label,
            total_cost
        ).outerjoin(
            AssetSector,
            AssetSector.id == Asset.sector_id
        )

        if asset_type_id is not None:
            query = query.filter(Asset.type_id == asset_type_id)

        rows = (
            query
            .group_by(sector_label)
            .order_by(total_cost.desc())
            .all()
        )

        return [
            {"label": sector, "value": float(total)}
            for sector, total in rows
            if total and total > 0
        ]

    def _base_allocation_query(self, year: int):
        subquery = (
            self.db.query(
                PositionSnapshot.asset_id,
                func.max(PositionSnapshot.snapshot_date).label("max_date"),
                func.max(PositionSnapshot.id).label("max_id")
            )
            .filter(func.extract("year", PositionSnapshot.snapshot_date) <= year)
            .group_by(PositionSnapshot.asset_id)
            .subquery()
        )

        total_cost = func.sum(
            PositionSnapshot.quantity * PositionSnapshot.avg_price
        ).label("total_cost")

        query = (
            self.db.query(total_cost)
            .select_from(Asset)
            .join(PositionSnapshot, PositionSnapshot.asset_id == Asset.id)
            .join(
                subquery,
                (PositionSnapshot.asset_id == subquery.c.asset_id) &
                (PositionSnapshot.id == subquery.c.max_id)
            )
        )

        return query, total_cost

    def rebuild_from(self, asset_id: int, from_date: Date, commit: bool = True) -> None:
        """
        Rebuild incremental snapshots for a single asset starting from a given date.

        Args:
            commit: Commit the rebuild. Pass False when the caller commits it
                together with the change that triggered it; on error the caller
                must roll back.

        Raises:
            ValidationException: If a SELL note exceeds the position at its date.

        Note:
            This method only rebuilds snapshots for the given asset_id.
            If there are CONVERSION events that generate snapshots for a different
            target asset, those target assets must be rebuilt explicitly by calling
            rebuild_from() for each affected asset.
        """
        try:
            self._delete_snapshots_from(asset_id, from_date)
            qty, cost = self._load_state_before(asset_id, from_date)
            timeline = self._load_timeline(asset_id, from_date)
            self._build_from_timeline(asset_id, timeline, qty, cost)

            if commit:
                self.repository.save_changes()
            else:
                self.db.flush()
        except Exception:
            self.repository.rollback()
            raise

    def _delete_snapshots_from(self, asset_id: int, from_date: Date) -> None:
        self.db.query(PositionSnapshot).filter(
            PositionSnapshot.asset_id == asset_id,
            PositionSnapshot.snapshot_date >= from_date
        ).delete(synchronize_session=False)

    def _load_state_before(self, asset_id: int, from_date: Date) -> tuple[Decimal, Decimal]:
        snapshot = (
            self.db.query(PositionSnapshot)
            .filter(
                PositionSnapshot.asset_id == asset_id,
                PositionSnapshot.snapshot_date < from_date
            )
            .order_by(
                PositionSnapshot.snapshot_date.desc(),
                PositionSnapshot.id.desc()
            )
            .first()
        )

        if not snapshot:
            return Decimal("0"), Decimal("0")

        return snapshot.quantity, snapshot.total_cost

    def _load_timeline(self, asset_id: int, from_date: Date) -> list:
        notes = (
            self.db.query(BrokerNote)
            .filter(
                BrokerNote.asset_id == asset_id,
                BrokerNote.date >= from_date,
            )
            .all()
        )

        events = (
            self.db.query(AssetEvent)
            .filter(
                AssetEvent.date >= from_date,
                or_(
                    AssetEvent.asset_id == asset_id,
                    and_(
                        AssetEvent.event_type == AssetEventType.TOTAL_CONVERSION,
                        AssetEvent.target_asset_id == asset_id
                    )
                )
            )
            .all()
        )

        timeline = notes + events

        # Same-day order: AssetEvents first, then BUY notes before SELL notes
        # (so day trades never sell from an empty position), then by id.
        timeline.sort(
            key=lambda x: (
                x.date,
                0 if isinstance(x, AssetEvent) else 1,
                1 if isinstance(x, BrokerNote) and x.operation == OperationType.SELL else 0,
                x.id
            )
        )

        return timeline

    def _build_from_timeline(self, asset_id: int, timeline: list, quantity: Decimal, total_cost: Decimal) -> None:
        for item in timeline:
            if isinstance(item, AssetEvent):
                quantity, total_cost = self._apply_asset_event(asset_id, item, quantity, total_cost)
                action = item.event_type.value.lower()

            elif isinstance(item, BrokerNote):
                quantity, total_cost = self._apply_broker_note(item, quantity, total_cost)
                action = item.operation.value.lower()

            self._add_snapshot(asset_id, item.date, quantity, total_cost, action)

    def _apply_asset_event(
            self, 
            asset_id: int, 
            event: AssetEvent, 
            quantity: Decimal, 
            total_cost: Decimal
        ) -> tuple[Decimal, Decimal]:

        match event.event_type:
            case AssetEventType.SPLIT | AssetEventType.REVERSE_SPLIT:
                if quantity <= 0:
                    return quantity, total_cost

                if not event.factor or event.factor <= 0:
                    return quantity, total_cost

                new_quantity = quantity / event.factor

                if new_quantity <= 0:
                    return Decimal("0"), Decimal("0")

                return new_quantity, total_cost

            case AssetEventType.AMORTIZATION:
                if quantity <= 0:
                    return quantity, total_cost

                event_quantity = event.quantity or quantity
                event_price = event.price or Decimal("0")

                amortized_value = event_quantity * event_price
                new_total_cost = total_cost - amortized_value

                if new_total_cost <= 0:
                    return quantity, Decimal("0")

                return quantity, new_total_cost

            case AssetEventType.SUBSCRIPTION:
                if quantity <= 0:
                    return quantity, total_cost

                event_quantity = event.quantity or Decimal("0")
                event_price = event.price or Decimal("0")

                added_cost = event_quantity * event_price

                return (
                    quantity + event_quantity,
                    total_cost + added_cost,
                )

            case AssetEventType.TOTAL_CONVERSION:
                if event.asset_id == asset_id:
                    return Decimal("0"), Decimal("0")

                if event.target_asset_id == asset_id:
                    target_qty = event.target_quantity or Decimal("0")
                    target_price = event.target_unit_price or Decimal("0")

                    if target_qty <= 0 or target_price <= 0:
                        return quantity, total_cost

                    added_cost = target_qty * target_price

                    return (
                        quantity + target_qty,
                        total_cost + added_cost
                    )

                return quantity, total_cost

            case _:
                return quantity, total_cost

    def _apply_broker_note(self, note: BrokerNote, quantity: Decimal, total_cost: Decimal) -> tuple[Decimal, Decimal]:
        if note.operation == OperationType.BUY:
            return (
                quantity + note.quantity,
                total_cost + note.total_value
            )

        if note.operation == OperationType.SELL:
            if note.quantity > quantity + QUANTITY_TOLERANCE:
                ticker = note.asset.ticker if note.asset else note.asset_id
                raise ValidationException(
                    f"Sell of {note.quantity:f} {ticker} on {note.date.isoformat()} "
                    f"exceeds the position of {quantity:f} at that date"
                )

            if quantity <= 0:
                return Decimal("0"), Decimal("0")

            avg_price = total_cost / quantity
            new_quantity = quantity - note.quantity
            new_cost = total_cost - (avg_price * note.quantity)

            if new_quantity <= 0:
                return Decimal("0"), Decimal("0")

            return new_quantity, new_cost

        return quantity, total_cost

    def _add_snapshot(
            self, 
            asset_id: int, 
            snapshot_date: Date, 
            quantity: Decimal, 
            total_cost: Decimal, 
            origin_action: str
        ) -> None:

        avg_price = total_cost / quantity if quantity > 0 else Decimal("0")

        self.db.add(
            PositionSnapshot(
                asset_id=asset_id,
                snapshot_date=snapshot_date,
                quantity=quantity,
                avg_price=avg_price,
                origin_action=origin_action
            )
        )
