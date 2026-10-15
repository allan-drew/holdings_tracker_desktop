from typing import List

from sqlalchemy.orm import Session, joinedload

from holdings_tracker_desktop.models.asset_sector import AssetSector
from holdings_tracker_desktop.repositories.base_repository import BaseRepository
from holdings_tracker_desktop.schemas.asset_sector import (
  AssetSectorCreate, AssetSectorUpdate, AssetSectorResponse
)

class AssetSectorService:
    def __init__(self, db: Session):
        self.repository = BaseRepository[AssetSector, AssetSectorCreate, AssetSectorUpdate](
            model=AssetSector,
            db=db
        )

    def create(self, data: AssetSectorCreate) -> AssetSectorResponse:
        """Create new AssetSector with validation"""
        asset_sector = self.repository.create_from_schema(data)
        return AssetSectorResponse.model_validate(asset_sector)

    def get(self, asset_sector_id: int) -> AssetSectorResponse:
        """Get AssetSector by ID"""
        asset_sector = self.repository.get_or_raise(asset_sector_id)
        return AssetSectorResponse.model_validate(asset_sector)

    def update(self, asset_sector_id: int, data: AssetSectorUpdate) -> AssetSectorResponse:
        """Update AssetSector"""
        updated = self.repository.update_from_schema(asset_sector_id, data)
        return AssetSectorResponse.model_validate(updated)

    def delete(self, asset_sector_id: int) -> bool:
        """Delete AssetSector"""
        asset_sector = self.repository.get_or_raise(asset_sector_id)

        error = asset_sector.validate_for_deletion()
        if error:
            raise error

        return self.repository.delete(asset_sector_id)

    def list_all_models(self, order_by: str = "name") -> List[AssetSector]:
        """Get all AssetSectors as SQLAlchemy models"""
        return self.repository.get_all(order_by=order_by)

    def list_all_for_ui(
        self, 
        skip: int = 0, 
        limit: int | None = None,
        order_by: str = "name",
        descending: bool = False
    ) -> List[dict]:
        """Get AssetSectors already formatted for UI"""
        asset_sectors = self.repository.get_all(skip, limit, order_by, descending)
        return [at.to_ui_dict() for at in asset_sectors]

    def count_all(self) -> int:
        """Count all AssetSectors"""
        return self.repository.count()

    def get_by_asset_type(self, asset_type_id: int) -> List[AssetSectorResponse]:
        """Get all AssetSectors for a asset type"""
        asset_sectors = self.repository.find_all_by(asset_type_id=asset_type_id)
        return [AssetSectorResponse.model_validate(at) for at in asset_sectors]

    def get_details(self, asset_sector_id: int) -> AssetSector:
        return (
            self.repository.db
            .query(AssetSector)
            .options(joinedload(AssetSector.asset_type))
            .filter(AssetSector.id == asset_sector_id)
            .first()
        )
