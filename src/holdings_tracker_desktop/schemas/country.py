from pydantic import Field, field_validator, model_validator
from pydantic_core import PydanticCustomError
from typing import Optional
from .base import BaseSchema, AuditableSchema

class CountryBase(BaseSchema):
    name: str = Field(..., min_length=2, max_length=80)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

class CountryCreate(CountryBase):
    model_config = {
        "extra": "forbid"
    }

class CountryUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=2, max_length=80)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v is not None else v

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

class CountryResponse(CountryBase, AuditableSchema):
    model_config = {
        "from_attributes": True
    }
