from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import AuditableModel
from holdings_tracker_desktop.utils.exceptions import ConflictException

if TYPE_CHECKING:
    from .asset import Asset
    from .asset_type import AssetType

class AssetSector(AuditableModel):
    __tablename__ = "asset_sectors"

    name: Mapped[str] = mapped_column(
        String(80), 
        nullable=False
    )

    asset_type_id: Mapped[int] = mapped_column(
        ForeignKey("asset_types.id"), 
        nullable=False
    )

    asset_type: Mapped[AssetType] = relationship(
        back_populates="sectors",
        cascade="save-update",
        lazy="selectin"
    )

    assets: Mapped[list[Asset]] = relationship(
        back_populates="sector",
        cascade="save-update",
        lazy="dynamic"
    )

    def to_response(self) -> dict:
        """Convert to dictionary compatible with AssetSectorResponse"""
        from holdings_tracker_desktop.schemas.asset_sector import AssetSectorResponse
        return AssetSectorResponse.model_validate(self).model_dump()

    @classmethod
    def from_create_schema(cls, schema_data: dict) -> AssetSector:
        """Create instance from creation schema"""
        from holdings_tracker_desktop.schemas.asset_sector import AssetSectorCreate

        validated_data = AssetSectorCreate(**schema_data).model_dump()
        return cls(**validated_data)

    def update_from_schema(self, schema_data: dict):
        """Update instance from update schema"""
        from holdings_tracker_desktop.schemas.asset_sector import AssetSectorUpdate

        update_data = AssetSectorUpdate(**schema_data).model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(self, key, value)

    @property
    def assets_count(self) -> int:
        return self.assets.count()

    def validate_for_deletion(self) -> ConflictException | None:
        """
        Validate if asset sector can be deleted.

        Returns:
            The ConflictException to raise, or None when it can be deleted
        """
        count = self.assets_count
        if count > 0:
            return ConflictException(
                f"Cannot delete '{self.name}' because it has {count} associated assets",
                "error_has_assets", name=self.name, count=count
            )

        return None

    def to_ui_dict(self) -> dict:
        """Optimized for PySide6 table widgets"""
        return {
            'id': self.id,
            'name': self.name,
            'asset_type_name': self.asset_type.name if self.asset_type else '',
            'assets_count': self.assets_count,
            'created_at': self.created_at_local.isoformat(),
            'updated_at': self.updated_at_local.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<AssetSector(id={self.id}, name={self.name}, asset_type_id={self.asset_type_id})>"
