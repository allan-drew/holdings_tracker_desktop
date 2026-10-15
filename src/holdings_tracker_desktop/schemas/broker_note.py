from datetime import date as Date
from decimal import Decimal
from typing import Optional
from pydantic import Field, field_validator, model_validator
from pydantic_core import PydanticCustomError
from .base import BaseSchema, AuditableSchema
from holdings_tracker_desktop.models.broker_note import OperationType

class BrokerNoteBase(BaseSchema):
    date: Date
    operation: OperationType
    broker_id: int = Field(..., gt=0)
    asset_id: int = Field(..., gt=0)

    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)

    fees: Decimal = Field(default=Decimal("0"), ge=0)
    taxes: Decimal = Field(default=Decimal("0"), ge=0)

    note_number: Optional[str] = Field(
        None,
        max_length=30
    )

    @field_validator("fees", "taxes", mode="before")
    @classmethod
    def default_missing_costs(cls, v: Decimal) -> Decimal:
        # Negative values are rejected by ge=0, as in BrokerNoteUpdate
        return Decimal("0") if v is None else v

class BrokerNoteCreate(BrokerNoteBase):
    model_config = {
        "extra": "forbid"
    }

class BrokerNoteUpdate(BaseSchema):
    date: Optional[Date] = None
    broker_id: Optional[int] = Field(None, gt=0)
    quantity: Optional[Decimal] = Field(None, gt=0)
    price: Optional[Decimal] = Field(None, gt=0)
    fees: Optional[Decimal] = Field(None, ge=0)
    taxes: Optional[Decimal] = Field(None, ge=0)

    note_number: Optional[str] = Field(
        None,
        max_length=30
    )

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        if not self.model_fields_set:
            raise PydanticCustomError(
                "no_fields_to_update", "At least one field must be provided for update"
            )
        return self

    model_config = {
        "extra": "forbid"
    }

class BrokerNoteResponse(BrokerNoteBase, AuditableSchema):
    total_value: Decimal

    model_config = {
        "from_attributes": True
    }
