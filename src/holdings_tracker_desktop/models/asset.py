from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .asset_event import AssetEventType
from .base import AuditableModel
from holdings_tracker_desktop.utils.exceptions import ConflictException

if TYPE_CHECKING:
    from .asset_event import AssetEvent
    from .asset_sector import AssetSector
    from .asset_type import AssetType
    from .broker_note import BrokerNote
    from .currency import Currency
    from .position_snapshot import PositionSnapshot
    from .asset_ticker_history import AssetTickerHistory

class Asset(AuditableModel):
    __tablename__ = "assets"

    ticker: Mapped[str] = mapped_column(
        String(12),
        unique=True, 
        nullable=False
    )

    type_id: Mapped[int] = mapped_column(
        ForeignKey("asset_types.id"), 
        nullable=False
    )

    currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"), 
        nullable=False
    )

    sector_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_sectors.id"), 
        nullable=True
    )

    asset_type: Mapped[AssetType] = relationship(
        back_populates="assets",
        cascade="save-update",
        lazy="selectin"
    )

    currency: Mapped[Currency] = relationship(
        back_populates="assets",
        cascade="save-update",
        lazy="selectin"
    )

    sector: Mapped[AssetSector | None] = relationship(
        back_populates="assets",
        cascade="save-update",
        lazy="selectin"
    )

    broker_notes: Mapped[list[BrokerNote]] = relationship(
        back_populates="asset",
        cascade="save-update",
        lazy="dynamic"
    )

    snapshots: Mapped[list[PositionSnapshot]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    events: Mapped[list[AssetEvent]] = relationship(
        back_populates="asset",
        foreign_keys="[AssetEvent.asset_id]",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    ticker_histories: Mapped[list[AssetTickerHistory]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    events_as_target: Mapped[list["AssetEvent"]] = relationship(
        back_populates="target_asset",
        foreign_keys="[AssetEvent.target_asset_id]"
    )

    def to_response(self) -> dict:
        """Convert to dictionary compatible with AssetResponse"""
        from holdings_tracker_desktop.schemas.asset import AssetResponse
        return AssetResponse.model_validate(self).model_dump()

    @classmethod
    def from_create_schema(cls, schema_data: dict) -> Asset:
        """Create instance from creation schema"""
        from holdings_tracker_desktop.schemas.asset import AssetCreate

        validated_data = AssetCreate(**schema_data).model_dump()
        return cls(**validated_data)

    def update_from_schema(self, schema_data: dict):
        """Update instance from update schema"""
        from holdings_tracker_desktop.schemas.asset import AssetUpdate

        update_data = AssetUpdate(**schema_data).model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(self, key, value)

    @property
    def broker_notes_count(self) -> int:
        return self.broker_notes.count()

    @property
    def snapshots_count(self) -> int:
        return self.snapshots.count()

    @property
    def events_count(self) -> int:
        return self.events.count()
    
    @property
    def ticker_histories_count(self) -> int:
        return self.ticker_histories.count()

    def validate_for_deletion(self) -> ConflictException | None:
        """
        Validate if asset can be deleted.
        
        Returns:
            The ConflictException to raise, or None when it can be deleted
        """
        count = self.broker_notes_count
        if count > 0:
            return ConflictException(
                f"Cannot delete '{self.ticker}' because it has {count} associated broker notes",
                "error_has_broker_notes", name=self.ticker, count=count
            )

        # Deleting either side of a conversion would leave the other asset's
        # position built from an event that no longer exists (or has no target).
        conversions = (
            self.events.filter_by(event_type=AssetEventType.TOTAL_CONVERSION).count()
            + len(self.events_as_target)
        )
        if conversions > 0:
            return ConflictException(
                f"Cannot delete '{self.ticker}' because it has {conversions} associated conversion events",
                "error_has_conversion_events", name=self.ticker, count=conversions
            )

        return None

    def to_ui_dict(self) -> dict:
        """Optimized for PySide6 table widgets"""
        return {
            'id': self.id,
            'ticker': self.ticker,
            'type_name': self.asset_type.name if self.asset_type else '',
            'currency_code': self.currency.code if self.currency else '',
            'sector_name': self.sector.name if self.sector else '',
            'broker_notes_count': self.broker_notes_count,
            'snapshots_count': self.snapshots_count,
            'events_count': self.events_count,
            'ticker_histories_count': self.ticker_histories_count,
            'created_at': self.created_at_local.isoformat(),
            'updated_at': self.updated_at_local.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, ticker={self.ticker}, type_id={self.type_id})>"
