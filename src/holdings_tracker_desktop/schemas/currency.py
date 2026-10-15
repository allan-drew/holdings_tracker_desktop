from pydantic import Field, field_validator, model_validator
from pydantic_core import PydanticCustomError
from typing import Optional
from .base import BaseSchema, AuditableSchema

class CurrencyBase(BaseSchema):
    code: str = Field(..., min_length=3, max_length=3)
    name: str = Field(..., min_length=2, max_length=80)
    symbol: str = Field(..., min_length=1, max_length=3)

    @field_validator("code", mode="before")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper() if isinstance(v, str) else v

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("symbol", mode="before")
    @classmethod
    def strip_symbol(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

class CurrencyCreate(CurrencyBase):
    model_config = {
        "extra": "forbid"
    }

class CurrencyUpdate(BaseSchema):
    code: Optional[str] = Field(None, min_length=3, max_length=3)
    name: Optional[str] = Field(None, min_length=2, max_length=80)
    symbol: Optional[str] = Field(None, min_length=1, max_length=3)

    @field_validator("code", mode="before")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper() if isinstance(v, str) else v

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("symbol", mode="before")
    @classmethod
    def strip_symbol(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

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

class CurrencyResponse(CurrencyBase, AuditableSchema):
    model_config = {
        "from_attributes": True
    }
