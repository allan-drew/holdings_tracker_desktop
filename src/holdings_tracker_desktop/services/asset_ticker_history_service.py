from typing import List

from sqlalchemy.orm import Session, joinedload

from holdings_tracker_desktop.models.asset_ticker_history import AssetTickerHistory
from holdings_tracker_desktop.repositories.base_repository import BaseRepository
from holdings_tracker_desktop.schemas.asset_ticker_history import (
  AssetTickerHistoryCreate, AssetTickerHistoryUpdate, AssetTickerHistoryResponse
)
from holdings_tracker_desktop.services.asset_service import AssetService
from holdings_tracker_desktop.utils.exceptions import (
    ConflictException, NotFoundException, ValidationException
)

class AssetTickerHistoryService:
    def __init__(self, db: Session):
        self.repository = BaseRepository[AssetTickerHistory, AssetTickerHistoryCreate, AssetTickerHistoryUpdate](
            model=AssetTickerHistory,
            db=db
        )

    def create(self, data: AssetTickerHistoryCreate) -> AssetTickerHistoryResponse:
        """Change Asset ticker and register history"""
        from holdings_tracker_desktop.models.asset import Asset

        db = self.repository.db

        asset = (
            db.query(Asset)
            .filter(Asset.id == data.asset_id)
            .one_or_none()
        )

        if not asset:
            raise NotFoundException("Asset not found")

        if asset.ticker == data.new_ticker:
            raise ValidationException(
                "New ticker must be different from current ticker", "error_ticker_unchanged"
            )

        AssetService(db).ensure_ticker_is_unique(data.new_ticker, exclude_id=asset.id)

        history = AssetTickerHistory(
            asset=asset,
            old_ticker=asset.ticker,
            new_ticker=data.new_ticker,
            change_date=data.change_date,
        )

        asset.ticker = data.new_ticker

        db.add(history)
        db.flush()

        return AssetTickerHistoryResponse.model_validate(history)

    def get(self, asset_ticker_history_id: int) -> AssetTickerHistoryResponse:
        """Get AssetTickerHistory by ID"""
        asset_ticker_history = self.repository.get_or_raise(asset_ticker_history_id)
        return AssetTickerHistoryResponse.model_validate(asset_ticker_history)

    def delete(self, asset_ticker_history_id: int) -> bool:
        """
        Delete the most recent ticker change of an asset and restore its
        previous ticker. Older changes cannot be deleted, since later changes
        were made on top of them.
        """
        db = self.repository.db
        history = self.repository.get_or_raise(asset_ticker_history_id)

        latest = (
            db.query(AssetTickerHistory)
            .filter(AssetTickerHistory.asset_id == history.asset_id)
            .order_by(AssetTickerHistory.change_date.desc(), AssetTickerHistory.id.desc())
            .first()
        )

        if latest.id != history.id:
            raise ConflictException(
                "Only the most recent ticker change can be deleted", "error_only_latest_ticker_change"
            )

        if history.old_ticker:
            AssetService(db).ensure_ticker_is_unique(history.old_ticker, exclude_id=history.asset_id)

        with self.repository.atomic():
            if history.old_ticker:
                history.asset.ticker = history.old_ticker

            return self.repository.delete(asset_ticker_history_id, commit=False)

    def list_all_for_ui(
        self,
        asset_id: int,
        skip: int = 0, 
        limit: int | None = None
    ) -> List[dict]:
        """Get AssetTickerHistories already formatted for UI"""
        asset_ticker_histories = (
            self.repository.db
            .query(AssetTickerHistory)
            .filter(AssetTickerHistory.asset_id == asset_id)
            .order_by(AssetTickerHistory.change_date.desc(), AssetTickerHistory.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [ath.to_ui_dict() for ath in asset_ticker_histories]

    def count_all(self) -> int:
        """Count all AssetTickerHistories"""
        return self.repository.count()

    def get_details(self, asset_ticker_history_id: int) -> AssetTickerHistory:
        return (
            self.repository.db
            .query(AssetTickerHistory)
            .options(joinedload(AssetTickerHistory.asset))
            .filter(AssetTickerHistory.id == asset_ticker_history_id)
            .first()
        )
