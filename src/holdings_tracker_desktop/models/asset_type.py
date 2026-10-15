from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import AuditableModel
from holdings_tracker_desktop.utils.exceptions import ConflictException

if TYPE_CHECKING:
    from .asset import Asset
    from .asset_sector import AssetSector
    from .country import Country

class AssetType(AuditableModel):
    __tablename__ = "asset_types"

    name: Mapped[str] = mapped_column(
        String(20), 
        unique=True, 
        nullable=False
    )

    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"),
        nullable=False
    )

    country: Mapped[Country] = relationship(
        back_populates="asset_types",
        cascade="save-update",
        lazy="selectin"
    )

    assets: Mapped[list[Asset]] = relationship(
        back_populates="asset_type",
        cascade="save-update",
        lazy="dynamic"
    )

    sectors: Mapped[list[AssetSector]] = relationship(
        back_populates="asset_type",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def to_response(self) -> dict:
        """Convert to dictionary compatible with AssetTypeResponse"""
        from holdings_tracker_desktop.schemas.asset_type import AssetTypeResponse
        return AssetTypeResponse.model_validate(self).model_dump()

    @classmethod
    def from_create_schema(cls, schema_data: dict) -> AssetType:
        """Create instance from creation schema"""
        from holdings_tracker_desktop.schemas.asset_type import AssetTypeCreate

        validated_data = AssetTypeCreate(**schema_data).model_dump()
        return cls(**validated_data)

    def update_from_schema(self, schema_data: dict):
        """Update instance from update schema"""
        from holdings_tracker_desktop.schemas.asset_type import AssetTypeUpdate

        update_data = AssetTypeUpdate(**schema_data).model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(self, key, value)

    @property
    def assets_count(self) -> int:
        return self.assets.count()

    @property
    def sectors_count(self) -> int:
        return self.sectors.count()

    def validate_for_deletion(self) -> ConflictException | None:
        """
        Validate if asset type can be deleted.
        
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
            'country_name': self.country.name if self.country else '',
            'assets_count': self.assets_count,
            'sectors_count': self.sectors_count,
            'created_at': self.created_at_local.isoformat(),
            'updated_at': self.updated_at_local.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<AssetType(id={self.id}, name={self.name}, country_id={self.country_id})>"
