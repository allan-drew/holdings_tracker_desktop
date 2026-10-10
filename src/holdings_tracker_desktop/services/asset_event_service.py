from typing import List

from sqlalchemy.orm import Session, joinedload

from holdings_tracker_desktop.models.asset_event import AssetEvent, AssetEventType
from holdings_tracker_desktop.repositories.base_repository import BaseRepository
from holdings_tracker_desktop.schemas.asset_event import (
  AssetEventCreate, AssetEventUpdate, AssetEventResponse
)
from holdings_tracker_desktop.services.position_snapshot_service import PositionSnapshotService

class AssetEventService:
    def __init__(self, db: Session):
        self.repository = BaseRepository[AssetEvent, AssetEventCreate, AssetEventUpdate](
            model=AssetEvent,
            db=db
        )
        self.position_snapshot_service = PositionSnapshotService(db)

    def create(self, data: AssetEventCreate) -> AssetEventResponse:
        """Create new AssetEvent with validation"""
        asset_event = self.repository.create_from_schema(data)

        self._rebuild_positions_for_event(
            event=asset_event,
            from_date=asset_event.date
        )

        return AssetEventResponse.model_validate(asset_event)

    def get(self, asset_event_id: int) -> AssetEventResponse:
        """Get AssetEvent by ID"""
        asset_event = self.repository.get_or_raise(asset_event_id)
        return AssetEventResponse.model_validate(asset_event)

    def update(self, asset_event_id: int, data: AssetEventUpdate) -> AssetEventResponse:
        """Update AssetEvent"""
        existing = self.repository.get_or_raise(asset_event_id)

        old_date = existing.date

        updated = self.repository.update_from_schema(asset_event_id, data)

        rebuild_from_date = min(old_date, updated.date)

        self._rebuild_positions_for_event(
            event=updated,
            from_date=rebuild_from_date
        )

        return AssetEventResponse.model_validate(updated)

    def delete(self, asset_event_id: int) -> bool:
        """Delete AssetEvent"""
        asset_event = self.repository.get_or_raise(asset_event_id)

        from_date = asset_event.date

        deleted = self.repository.delete(asset_event_id)

        if deleted:
            self._rebuild_positions_for_event(
                event=asset_event,
                from_date=from_date
            )

        return deleted

    def list_all_for_ui(
        self,
        asset_id: int,
        skip: int = 0, 
        limit: int | None = None
    ) -> List[dict]:
        """Get AssetEvents already formatted for UI"""
        asset_events = (
            self.repository.db
            .query(AssetEvent)
            .filter(AssetEvent.asset_id == asset_id)
            .order_by(AssetEvent.date.desc(), AssetEvent.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [ae.to_ui_dict() for ae in asset_events]

    def count_all(self) -> int:
        """Count all AssetEvents"""
        return self.repository.count()

    def get_details(self, asset_event_id: int) -> AssetEvent:
        return (
            self.repository.db
            .query(AssetEvent)
            .options(
                joinedload(AssetEvent.asset),
                joinedload(AssetEvent.target_asset),
            )
            .filter(AssetEvent.id == asset_event_id)
            .first()
        )

    def _rebuild_positions_for_event(self, event: AssetEvent, from_date):
        """
        Rebuild position snapshots affected by this event.

        Note:
            Conversion events affect two assets:
            - the source asset (event.asset_id)
            - the target asset (event.target_asset_id)

            For this reason, snapshot rebuild must be triggered explicitly
            for both assets.
        """
        self.repository.db.flush()

        self.position_snapshot_service.rebuild_from(
            asset_id=event.asset_id,
            from_date=from_date
        )

        if (
            event.event_type == AssetEventType.TOTAL_CONVERSION
            and event.target_asset_id
        ):
            self.position_snapshot_service.rebuild_from(
                asset_id=event.target_asset_id,
                from_date=from_date
            )

        self.repository.save_changes()
