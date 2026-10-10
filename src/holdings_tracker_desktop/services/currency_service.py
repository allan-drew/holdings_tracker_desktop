from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from holdings_tracker_desktop.models.currency import Currency
from holdings_tracker_desktop.repositories.base_repository import BaseRepository
from holdings_tracker_desktop.schemas.currency import (
  CurrencyCreate, CurrencyUpdate, CurrencyResponse
)
from holdings_tracker_desktop.utils.exceptions import ConflictException

class CurrencyService:
    def __init__(self, db: Session):
        self.repository = BaseRepository[Currency, CurrencyCreate, CurrencyUpdate](
            model=Currency,
            db=db
        )

    def create(self, data: CurrencyCreate) -> CurrencyResponse:
        """Create new Currency with validation"""
        self._ensure_code_is_unique(data.code)

        currency = self.repository.create_from_schema(data)
        return CurrencyResponse.model_validate(currency)

    def get(self, currency_id: int) -> CurrencyResponse:
        """Get Currency by ID"""
        currency = self.repository.get_or_raise(currency_id)
        return CurrencyResponse.model_validate(currency)

    def update(self, currency_id: int, data: CurrencyUpdate) -> CurrencyResponse:
        """Update Currency"""
        if "code" in data.model_fields_set:
            self._ensure_code_is_unique(data.code, exclude_id=currency_id)

        updated = self.repository.update_from_schema(currency_id, data)
        return CurrencyResponse.model_validate(updated)

    def delete(self, currency_id: int) -> bool:
        """Delete Currency"""
        currency = self.repository.get_or_raise(currency_id)

        can_delete, error_message = currency.validate_for_deletion()
        if not can_delete:
            raise ConflictException(error_message)

        return self.repository.delete(currency_id)

    def list_all_models(self, order_by: str = "code") -> List[Currency]:
        """Get all Currencies as SQLAlchemy models"""
        return self.repository.get_all(order_by=order_by)

    def list_all_for_ui(
        self, 
        skip: int = 0, 
        limit: int | None = None,
        order_by: str = "code",
        descending: bool = False
    ) -> List[dict]:
        """Get Currencies already formatted for UI"""
        currencies = self.repository.get_all(skip, limit, order_by, descending)
        return [c.to_ui_dict() for c in currencies]

    def count_all(self) -> int:
        """Count all Currencies"""
        return self.repository.count()

    def _ensure_code_is_unique(
        self,
        code: str,
        exclude_id: int | None = None
    ) -> None:
        """
        Validate that Currency code is unique (case-insensitive).
        """
        query = (
            self.repository.db.query(Currency)
            .filter(func.lower(Currency.code) == code.lower())
        )

        if exclude_id is not None:
            query = query.filter(Currency.id != exclude_id)

        if self.repository.db.query(query.exists()).scalar():
            raise ConflictException(
                f"Currency '{code}' already exists"
            )

    def get_details(self, currency_id: int) -> Currency:
        return (
            self.repository.db
            .query(Currency)
            .filter(Currency.id == currency_id)
            .first()
        )
