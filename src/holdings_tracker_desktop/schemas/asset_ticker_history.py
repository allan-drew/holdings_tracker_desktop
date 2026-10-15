from datetime import date as Date
from typing import Optional
from pydantic import Field, field_validator
from .base import BaseSchema, AuditableSchema

class AssetTickerHistoryBase(BaseSchema):
    asset_id: int = Field(..., gt=0)
    old_ticker: Optional[str] = None
    new_ticker: str = Field(..., min_length=1, max_length=12)
    change_date: Date

    @field_validator("old_ticker", "new_ticker", mode="before")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.strip().upper() if isinstance(v, str) else v

class AssetTickerHistoryCreate(AssetTickerHistoryBase):
    model_config = {
        "extra": "forbid"
    }

class AssetTickerHistoryUpdate(BaseSchema):
    pass

class AssetTickerHistoryResponse(AssetTickerHistoryBase, AuditableSchema):
    model_config = {
        "from_attributes": True
    }
