from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Enum, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from enum import Enum as PyEnum
from decimal import Decimal
from .base import AuditableModel
from holdings_tracker_desktop.utils.exceptions import ValidationException

if TYPE_CHECKING:
    from .asset import Asset
    from .broker import Broker

class OperationType(PyEnum):
    BUY = "BUY"
    SELL = "SELL"

class BrokerNote(AuditableModel):
    __tablename__ = "broker_notes"

    date: Mapped[Date] = mapped_column(
        Date, 
        nullable=False
    )

    operation: Mapped[OperationType] = mapped_column(
        Enum(OperationType), 
        nullable=False
    )

    broker_id: Mapped[int] = mapped_column(
        ForeignKey("brokers.id"), 
        nullable=False
    )

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"), 
        nullable=False
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), 
        nullable=False
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), 
        nullable=False
    )

    fees: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), 
        default=0
    )

    taxes: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), 
        default=0
    )

    note_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    broker: Mapped[Broker] = relationship(
        back_populates="broker_notes",
        cascade="save-update",
        lazy="selectin"
    )

    asset: Mapped[Asset] = relationship(
        back_populates="broker_notes",
        cascade="save-update",
        lazy="selectin"
    )

    @validates("operation")
    def _validate_operation(self, key, value):
        if self.id is not None and value != self.operation:
            raise ValidationException("Operation cannot be changed", "error_operation_cannot_change")
        return value

    def to_response(self) -> dict:
        """Convert to dictionary compatible with BrokerNoteResponse"""
        from holdings_tracker_desktop.schemas.broker_note import BrokerNoteResponse
        return BrokerNoteResponse.model_validate(self).model_dump()

    @classmethod
    def from_create_schema(cls, schema_data: dict) -> BrokerNote:
        """Create instance from creation schema"""
        from holdings_tracker_desktop.schemas.broker_note import BrokerNoteCreate

        validated_data = BrokerNoteCreate(**schema_data).model_dump()
        return cls(**validated_data)

    def update_from_schema(self, schema_data: dict):
        """Update instance from update schema"""
        from holdings_tracker_desktop.schemas.broker_note import BrokerNoteUpdate

        update_data = BrokerNoteUpdate(**schema_data).model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(self, key, value)

    @property
    def total_value(self):
        """Amount paid on a BUY (costs added) or received on a SELL (costs deducted)."""
        gross = self.quantity * self.price
        costs = (self.fees or 0) + (self.taxes or 0)

        if self.operation == OperationType.SELL:
            return gross - costs

        return gross + costs

    def to_ui_dict(self) -> dict:
        """Optimized for PySide6 table widgets"""
        return {
            'id': self.id,
            'date': self.date,
            'operation': self.operation,
            'broker_name': self.broker.name if self.broker else '',
            'asset_ticker': self.asset.ticker if self.asset else '',
            'asset_currency': self.asset.currency.symbol if self.asset else '',
            'quantity': self.quantity,
            'price': self.price,
            'fees': self.fees,
            'taxes': self.taxes,
            'note_number': self.note_number if self.note_number else '',
            'total_value': self.total_value,
            'created_at': self.created_at_local.isoformat(),
            'updated_at': self.updated_at_local.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<BrokerNote(id={self.id}, date={self.date}, operation={self.operation}, asset_id={self.asset_id})>"
