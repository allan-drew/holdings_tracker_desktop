from pydantic import Field, field_validator, model_validator
from pydantic_core import PydanticCustomError
from typing import Optional
from .base import BaseSchema, AuditableSchema

class AssetBase(BaseSchema):
    ticker: str = Field(..., min_length=1, max_length=12)
    type_id: int = Field(..., gt=0)
    currency_id: int = Field(..., gt=0)
    sector_id: Optional[int] = Field(None, gt=0)

    @field_validator("ticker", mode="before")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.strip().upper()

class AssetCreate(AssetBase):
    model_config = {
        "extra": "forbid"
    }

class AssetUpdate(BaseSchema):
    type_id: Optional[int] = Field(None, gt=0)
    currency_id: Optional[int] = Field(None, gt=0)
    sector_id: Optional[int] = Field(None, gt=0)

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

class AssetResponse(AssetBase, AuditableSchema):
    model_config = {
        "from_attributes": True
    }
