from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from holdings_tracker_desktop.models.broker import Broker
from holdings_tracker_desktop.repositories.base_repository import BaseRepository
from holdings_tracker_desktop.schemas.broker import (
  BrokerCreate, BrokerUpdate, BrokerResponse
)
from holdings_tracker_desktop.utils.exceptions import ConflictException

class BrokerService:
    def __init__(self, db: Session):
        self.repository = BaseRepository[Broker, BrokerCreate, BrokerUpdate](
            model=Broker,
            db=db
        )

    def create(self, data: BrokerCreate) -> BrokerResponse:
        """Create new Broker with validation"""
        self._ensure_name_is_unique(data.name)

        broker = self.repository.create_from_schema(data)
        return BrokerResponse.model_validate(broker)

    def get(self, broker_id: int) -> BrokerResponse:
        """Get Broker by ID"""
        broker = self.repository.get_or_raise(broker_id)
        return BrokerResponse.model_validate(broker)

    def update(self, broker_id: int, data: BrokerUpdate) -> BrokerResponse:
        """Update Broker"""
        if "name" in data.model_fields_set:
            self._ensure_name_is_unique(data.name, exclude_id=broker_id)

        updated = self.repository.update_from_schema(broker_id, data)
        return BrokerResponse.model_validate(updated)

    def delete(self, broker_id: int) -> bool:
        """Delete Broker"""
        broker = self.repository.get_or_raise(broker_id)

        error = broker.validate_for_deletion()
        if error:
            raise error

        return self.repository.delete(broker_id)

    def list_all_models(self, order_by: int = "id") -> List[Broker]:
        """Get all Countries as SQLAlchemy models"""
        return self.repository.get_all(order_by=order_by)

    def list_all_for_ui(
        self, 
        skip: int = 0, 
        limit: int | None = None,
        order_by: str = "name",
        descending: bool = False
    ) -> List[dict]:
        """Get Brokers already formatted for UI"""
        brokers = self.repository.get_all(skip, limit, order_by, descending)
        return [at.to_ui_dict() for at in brokers]

    def count_all(self) -> int:
        """Count all Brokers"""
        return self.repository.count()

    def get_by_country(self, country_id: int) -> List[BrokerResponse]:
        """Get all Brokers for a country"""
        brokers = self.repository.find_all_by(country_id=country_id)
        return [BrokerResponse.model_validate(at) for at in brokers]

    def _ensure_name_is_unique(
        self,
        name: str,
        exclude_id: int | None = None
    ) -> None:
        """
        Validate that broker name is unique (case-insensitive).
        """
        query = (
            self.repository.db.query(Broker)
            .filter(func.lower(Broker.name) == name.lower())
        )

        if exclude_id is not None:
            query = query.filter(Broker.id != exclude_id)

        if self.repository.db.query(query.exists()).scalar():
            raise ConflictException(
                f"Broker '{name}' already exists",
                "error_already_exists", name=name
            )

    def get_details(self, broker_id: int) -> Broker:
        return (
            self.repository.db
            .query(Broker)
            .options(joinedload(Broker.country))
            .filter(Broker.id == broker_id)
            .first()
        )
