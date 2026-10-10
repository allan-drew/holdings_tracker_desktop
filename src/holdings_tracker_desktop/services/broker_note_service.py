from datetime import date as Date
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from holdings_tracker_desktop.models.broker_note import BrokerNote
from holdings_tracker_desktop.repositories.base_repository import BaseRepository
from holdings_tracker_desktop.schemas.broker_note import (
  BrokerNoteCreate, BrokerNoteUpdate, BrokerNoteResponse
)
from holdings_tracker_desktop.services.position_snapshot_service import PositionSnapshotService

class BrokerNoteService:
    def __init__(self, db: Session):
        self.repository = BaseRepository[BrokerNote, BrokerNoteCreate, BrokerNoteUpdate](
            model=BrokerNote,
            db=db
        )
        self.position_snapshot_service = PositionSnapshotService(db)

    def create(self, data: BrokerNoteCreate) -> BrokerNoteResponse:
        """Create new BrokerNote with validation"""
        broker_note = self.repository.create_from_schema(data)

        self.position_snapshot_service.rebuild_from(
            asset_id=broker_note.asset_id,
            from_date=broker_note.date
        )

        return BrokerNoteResponse.model_validate(broker_note)

    def get(self, broker_note_id: int) -> BrokerNoteResponse:
        """Get BrokerNote by ID"""
        broker_note = self.repository.get_or_raise(broker_note_id)
        return BrokerNoteResponse.model_validate(broker_note)

    def update(self, broker_note_id: int, data: BrokerNoteUpdate) -> BrokerNoteResponse:
        """Update BrokerNote"""
        existing = self.repository.get_or_raise(broker_note_id)

        old_date = existing.date
        asset_id = existing.asset_id

        updated = self.repository.update_from_schema(broker_note_id, data)

        rebuild_from_date = min(old_date, updated.date)

        self.position_snapshot_service.rebuild_from(
            asset_id=asset_id,
            from_date=rebuild_from_date
        )

        return BrokerNoteResponse.model_validate(updated)

    def delete(self, broker_note_id: int) -> bool:
        """Delete BrokerNote"""
        broker_note = self.repository.get_or_raise(broker_note_id)

        asset_id = broker_note.asset_id
        from_date = broker_note.date

        deleted = self.repository.delete(broker_note_id)

        if deleted:
            self.position_snapshot_service.rebuild_from(
                asset_id=asset_id,
                from_date=from_date
            )

        return deleted

    def list_by_year_for_ui(
        self,
        year: int,
        skip: int = 0,
        limit: int | None = None,
        order_by: Date = "date",
        descending: bool = True
    ) -> List[dict]:
        query = (
            self.repository.db
            .query(BrokerNote)
            .filter(func.extract("year", BrokerNote.date) == year)
        )

        column = getattr(BrokerNote, order_by) if isinstance(order_by, str) else order_by

        if descending:
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())

        broker_notes = (
            query
            .offset(skip)
            .limit(limit)
            .all()
        )

        return [bn.to_ui_dict() for bn in broker_notes]

    def list_available_years(self) -> list[int]:
        rows = (
            self.repository.db
            .query(func.extract("year", BrokerNote.date).label("year"))
            .distinct()
            .order_by(func.extract("year", BrokerNote.date).desc())
            .all()
        )

        return [int(year) for (year,) in rows]

    def count_all(self) -> int:
        """Count all BrokerNotes"""
        return self.repository.count()

    def get_details(self, broker_note_id: int) -> BrokerNote:
        return (
            self.repository.db
            .query(BrokerNote)
            .options(joinedload(BrokerNote.broker))
            .options(joinedload(BrokerNote.asset))
            .filter(BrokerNote.id == broker_note_id)
            .first()
        )
