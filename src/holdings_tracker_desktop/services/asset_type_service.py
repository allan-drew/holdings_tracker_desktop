from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from holdings_tracker_desktop.models.asset_type import AssetType
from holdings_tracker_desktop.repositories.base_repository import BaseRepository
from holdings_tracker_desktop.schemas.asset_type import (
  AssetTypeCreate, AssetTypeUpdate, AssetTypeResponse
)
from holdings_tracker_desktop.utils.exceptions import ConflictException

class AssetTypeService:
    def __init__(self, db: Session):
        self.repository = BaseRepository[AssetType, AssetTypeCreate, AssetTypeUpdate](
            model=AssetType,
            db=db
        )

    def create(self, data: AssetTypeCreate) -> AssetTypeResponse:
        """Create new AssetType with validation"""
        self._ensure_name_is_unique(data.name)

        asset_type = self.repository.create_from_schema(data)
        return AssetTypeResponse.model_validate(asset_type)

    def get(self, asset_type_id: int) -> AssetTypeResponse:
        """Get AssetType by ID"""
        asset_type = self.repository.get_or_raise(asset_type_id)
        return AssetTypeResponse.model_validate(asset_type)

    def update(self, asset_type_id: int, data: AssetTypeUpdate) -> AssetTypeResponse:
        """Update AssetType"""
        if "name" in data.model_fields_set:
            self._ensure_name_is_unique(data.name, exclude_id=asset_type_id)

        updated = self.repository.update_from_schema(asset_type_id, data)
        return AssetTypeResponse.model_validate(updated)

    def delete(self, asset_type_id: int) -> bool:
        """Delete AssetType"""
        asset_type = self.repository.get_or_raise(asset_type_id)

        can_delete, error_message = asset_type.validate_for_deletion()
        if not can_delete:
            raise ConflictException(error_message)

        return self.repository.delete(asset_type_id)

    def list_all_models(self, order_by: str = "name") -> List[AssetType]:
        """Get all AssetTypes as SQLAlchemy models"""
        return self.repository.get_all(order_by=order_by)

    def list_all_for_ui(
        self, 
        skip: int = 0, 
        limit: int | None = None,
        order_by: str = "name",
        descending: bool = False
    ) -> List[dict]:
        """Get AssetTypes already formatted for UI"""
        asset_types = self.repository.get_all(skip, limit, order_by, descending)
        return [at.to_ui_dict() for at in asset_types]

    def count_all(self) -> int:
        """Count all AssetTypes"""
        return self.repository.count()

    def get_by_country(self, country_id: int) -> List[AssetTypeResponse]:
        """Get all AssetTypes for a country"""
        asset_types = self.repository.find_all_by(country_id=country_id)
        return [AssetTypeResponse.model_validate(at) for at in asset_types]

    def _ensure_name_is_unique(
        self,
        name: str,
        exclude_id: int | None = None
    ) -> None:
        """
        Validate that asset type name is unique (case-insensitive).
        """
        query = (
            self.repository.db.query(AssetType)
            .filter(func.lower(AssetType.name) == name.lower())
        )

        if exclude_id is not None:
            query = query.filter(AssetType.id != exclude_id)

        if self.repository.db.query(query.exists()).scalar():
            raise ConflictException(
                f"Asset Type '{name}' already exists"
            )

    def get_details(self, asset_type_id: int) -> AssetType:
        return (
            self.repository.db
            .query(AssetType)
            .options(joinedload(AssetType.country))
            .filter(AssetType.id == asset_type_id)
            .first()
        )
