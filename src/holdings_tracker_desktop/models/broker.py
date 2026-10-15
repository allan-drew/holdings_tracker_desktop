from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import AuditableModel
from holdings_tracker_desktop.utils.exceptions import ConflictException

if TYPE_CHECKING:
    from .broker_note import BrokerNote
    from .country import Country

class Broker(AuditableModel):
    __tablename__ = "brokers"

    name: Mapped[str] = mapped_column(
        String(80), 
        unique=True, 
        nullable=False
    )

    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id"), 
        nullable=False
    )

    country: Mapped[Country] = relationship(
        back_populates="brokers",
        cascade="save-update",
        lazy="selectin"
    )

    broker_notes: Mapped[list[BrokerNote]] = relationship(
        back_populates="broker",
        cascade="save-update",
        lazy="dynamic"
    )

    def to_response(self) -> dict:
        """Convert to dictionary compatible with BrokerResponse"""
        from holdings_tracker_desktop.schemas.broker import BrokerResponse
        return BrokerResponse.model_validate(self).model_dump()

    @classmethod
    def from_create_schema(cls, schema_data: dict) -> Broker:
        """Create instance from creation schema"""
        from holdings_tracker_desktop.schemas.broker import BrokerCreate

        validated_data = BrokerCreate(**schema_data).model_dump()
        return cls(**validated_data)

    def update_from_schema(self, schema_data: dict):
        """Update instance from update schema"""
        from holdings_tracker_desktop.schemas.broker import BrokerUpdate

        update_data = BrokerUpdate(**schema_data).model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(self, key, value)

    @property
    def broker_notes_count(self) -> int:
        return self.broker_notes.count()

    def validate_for_deletion(self) -> ConflictException | None:
        """
        Validate if broker can be deleted.

        Returns:
            The ConflictException to raise, or None when it can be deleted
        """
        count = self.broker_notes_count
        if count > 0:
            return ConflictException(
                f"Cannot delete '{self.name}' because it has {count} associated broker notes",
                "error_has_broker_notes", name=self.name, count=count
            )

        return None

    def to_ui_dict(self) -> dict:
        """Optimized for PySide6 table widgets"""
        return {
            'id': self.id,
            'name': self.name,
            'country_name': self.country.name if self.country else None,
            'broker_notes_count': self.broker_notes_count,
            'created_at': self.created_at_local.isoformat(),
            'updated_at': self.updated_at_local.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Broker(id={self.id}, name={self.name}, country_id={self.country_id})>"
