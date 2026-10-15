from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Enum, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from enum import Enum as PyEnum
from decimal import Decimal
from .base import AuditableModel
from holdings_tracker_desktop.utils.exceptions import ValidationException

if TYPE_CHECKING:
    from .asset import Asset

class AssetEventType(PyEnum):
    # Corporate Actions
    SPLIT = "SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"

    # Financial Events
    AMORTIZATION = "AMORTIZATION"
    SUBSCRIPTION = "SUBSCRIPTION"

    # Conversion Event
    TOTAL_CONVERSION = "TOTAL_CONVERSION"

class AssetEvent(AuditableModel):
    __tablename__ = "asset_events"

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"), 
        nullable=False
    )

    event_type: Mapped[AssetEventType] = mapped_column(
        Enum(AssetEventType), 
        nullable=False
    )

    date: Mapped[Date] = mapped_column(
        Date, 
        nullable=False
    )

    # Used only for SPLIT/REVERSE_SPLIT.
    factor: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)

    # Used only for AMORTIZATION/SUBSCRIPTION.
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)

    # Used only for TOTAL_CONVERSION.
    target_asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    target_quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    target_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    residual_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)

    asset: Mapped[Asset] = relationship(
        back_populates="events",
        foreign_keys=[asset_id],
        cascade="save-update",
        lazy="selectin"
    )

    target_asset: Mapped[Asset] = relationship(
        back_populates="events_as_target",
        foreign_keys=[target_asset_id]
    )

    @validates("event_type")
    def _validate_event_type(self, key, value):
        if self.id is not None and value != self.event_type:
            raise ValidationException("Type cannot be changed", "error_type_cannot_change")
        return value

    @validates("target_asset_id")
    def _validate_conversion_target(self, key, value):
        if (
            self.event_type == AssetEventType.TOTAL_CONVERSION
            and value is not None
            and self.asset_id is not None
            and value == self.asset_id
        ):
            raise ValidationException(
                "Conversion target asset must be different from source asset",
                "error_conversion_target_same_asset"
            )

        return value

    def to_response(self) -> dict:
        """Convert to dictionary compatible with AssetEventResponse"""
        from holdings_tracker_desktop.schemas.asset_event import AssetEventResponse
        return AssetEventResponse.model_validate(self).model_dump()

    @classmethod
    def from_create_schema(cls, schema_data: dict) -> AssetEvent:
        """Create instance from creation schema"""
        from holdings_tracker_desktop.schemas.asset_event import AssetEventCreate

        validated_data = AssetEventCreate(**schema_data).model_dump()
        return cls(**validated_data)

    def update_from_schema(self, schema_data: dict):
        """Update instance from update schema"""
        from holdings_tracker_desktop.schemas.asset_event import AssetEventUpdate

        update_data = AssetEventUpdate(**schema_data).model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(self, key, value)

    def to_ui_dict(self) -> dict:
        """Optimized for PySide6 table widgets"""
        return {
            'id': self.id,
            'asset_ticker': self.asset.ticker if self.asset else '',
            'event_type': self.event_type,
            'date': self.date,
            'factor': self.factor,
            'quantity': self.quantity,
            'price': self.price,
            'target_asset_id': self.target_asset_id,
            'target_quantity': self.target_quantity,
            'target_unit_price': self.target_unit_price,
            'residual_value': self.residual_value,
            'created_at': self.created_at_local.isoformat(),
            'updated_at': self.updated_at_local.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<AssetEventType(id={self.id}, asset_id={self.asset_id}, event_type={self.event_type})>"
