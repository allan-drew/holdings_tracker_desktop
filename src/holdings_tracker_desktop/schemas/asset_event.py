from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import Field, model_validator
from pydantic_core import PydanticCustomError
from .base import BaseSchema, AuditableSchema
from ..models.asset_event import AssetEventType

REQUIRED_FIELDS_BY_EVENT_TYPE: dict[str, set[str]] = {
    "SPLIT": {"factor"},
    "REVERSE_SPLIT": {"factor"},

    "AMORTIZATION": {"quantity", "price"},
    "SUBSCRIPTION": {"quantity", "price"},

    "TOTAL_CONVERSION": {
        "target_asset_id",
        "target_quantity",
        "target_unit_price",
    }
}

def _validate_fields_by_event_type(event: "AssetEventBase") -> None:
    required_fields = REQUIRED_FIELDS_BY_EVENT_TYPE.get(
        event.event_type.value, set()
    )

    missing_fields = [
        field
        for field in required_fields
        if getattr(event, field) is None
    ]

    if missing_fields:
        raise PydanticCustomError(
            "missing_event_fields",
            "Missing required fields for event_type={event_type}: {fields}",
            {"event_type": event.event_type.value, "fields": ", ".join(sorted(missing_fields))}
        )

    # Position rebuild divides quantity by factor, so a split (1:N) must be
    # entered as 1/N (< 1) and a reverse split (N:1) as N (> 1).
    if event.event_type == AssetEventType.SPLIT and event.factor >= 1:
        raise PydanticCustomError(
            "split_factor_range", "Split factor must be less than 1 (e.g. 1:10 -> 0.1)"
        )

    if event.event_type == AssetEventType.REVERSE_SPLIT and event.factor <= 1:
        raise PydanticCustomError(
            "reverse_split_factor_range", "Reverse split factor must be greater than 1 (e.g. 10:1 -> 10)"
        )

class AssetEventBase(BaseSchema):
    asset_id: int = Field(..., gt=0)
    event_type: AssetEventType
    date: date

    factor: Optional[Decimal] = Field(None, gt=0)

    quantity: Optional[Decimal] = Field(None, gt=0)
    price: Optional[Decimal] = Field(None, gt=0)

    target_asset_id: Optional[int] = Field(None, gt=0)
    target_quantity: Optional[Decimal] = Field(None, gt=0)
    target_unit_price: Optional[Decimal] = Field(None, gt=0)
    residual_value: Optional[Decimal] = Field(None, ge=0)

class AssetEventCreate(AssetEventBase):

    @model_validator(mode="after")
    def validate_fields_by_event_type(self):
        _validate_fields_by_event_type(self)
        return self

    model_config = {
        "extra": "forbid"
    }

class AssetEventUpdate(AssetEventBase):

    @model_validator(mode="after")
    def validate_fields_by_event_type(self):
        _validate_fields_by_event_type(self)
        return self

    model_config = {
        "extra": "forbid"
    }

class AssetEventResponse(AssetEventBase, AuditableSchema):
    model_config = {
        "from_attributes": True
    }
