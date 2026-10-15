from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from holdings_tracker_desktop.models.country import Country
from holdings_tracker_desktop.repositories.base_repository import BaseRepository
from holdings_tracker_desktop.schemas.country import ( 
  CountryCreate, CountryUpdate, CountryResponse
)
from holdings_tracker_desktop.utils.exceptions import ConflictException

class CountryService:
    def __init__(self, db: Session):
        self.repository = BaseRepository[Country, CountryCreate, CountryUpdate](
            model=Country,
            db=db
        )

    def create(self, data: CountryCreate) -> CountryResponse:
        """Create new Country with validation"""
        self._ensure_name_is_unique(data.name)

        country = self.repository.create_from_schema(data)
        return CountryResponse.model_validate(country)

    def get(self, country_id: int) -> CountryResponse:
        """Get Country by ID"""
        country = self.repository.get_or_raise(country_id)
        return CountryResponse.model_validate(country)

    def update(self, country_id: int, data: CountryUpdate) -> CountryResponse:
        """Update Country"""
        if "name" in data.model_fields_set:
            self._ensure_name_is_unique(data.name, exclude_id=country_id)

        updated = self.repository.update_from_schema(country_id, data)
        return CountryResponse.model_validate(updated)

    def delete(self, country_id: int) -> bool:
        """Delete Country"""
        country = self.repository.get_or_raise(country_id)

        error = country.validate_for_deletion()
        if error:
            raise error

        return self.repository.delete(country_id)

    def list_all_models(self, order_by: str = "name") -> List[Country]:
        """Get all Countries as SQLAlchemy models"""
        return self.repository.get_all(order_by=order_by)

    def list_all_for_ui(
        self, 
        skip: int = 0, 
        limit: int | None = None,
        order_by: str = "name",
        descending: bool = False
    ) -> List[dict]:
        """Get Countries already formatted for UI"""
        countries = self.repository.get_all(skip, limit, order_by, descending)
        return [c.to_ui_dict() for c in countries]

    def count_all(self) -> int:
        """Count all Countries"""
        return self.repository.count()

    def _ensure_name_is_unique(
        self,
        name: str,
        exclude_id: int | None = None
    ) -> None:
        """
        Validate that country name is unique (case-insensitive).
        """
        query = (
            self.repository.db.query(Country)
            .filter(func.lower(Country.name) == name.lower())
        )

        if exclude_id is not None:
            query = query.filter(Country.id != exclude_id)

        if self.repository.db.query(query.exists()).scalar():
            raise ConflictException(
                f"Country '{name}' already exists",
                "error_already_exists", name=name
            )

    def get_details(self, country_id: int) -> Country:
        return (
            self.repository.db
            .query(Country)
            .filter(Country.id == country_id)
            .first()
        )
