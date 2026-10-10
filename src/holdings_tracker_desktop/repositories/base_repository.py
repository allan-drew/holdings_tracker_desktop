from contextlib import contextmanager
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import asc, desc, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from typing import Generic, TypeVar, Optional, List, Any, Dict

from holdings_tracker_desktop.models.base import IdentifiedModel as SQLAlchemyBaseModel
from holdings_tracker_desktop.utils.exceptions import (
    NotFoundException,
    DatabaseException,
    ConflictException
)

# Type variables for generic repository
ModelType = TypeVar("ModelType", bound=SQLAlchemyBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=PydanticBaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=PydanticBaseModel)

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base repository with CRUD operations for SQLAlchemy models.
    
    This repository pattern provides a clean abstraction over database operations
    and integrates well with Pydantic schemas.
    """
    
    def __init__(self, model: type[ModelType], db: Session):
        """
        Initialize repository with model and database session.
        
        Args:
            model: SQLAlchemy model class
            db: SQLAlchemy database session
        """
        self.model = model
        self.db = db

    # =========================================================================
    # BASIC CRUD OPERATIONS
    # =========================================================================

    def get(self, id: int) -> Optional[ModelType]:
        """
        Get a single record by ID.

        Args:
            id: Record ID

        Returns:
            Model instance or None if not found
        """
        try:
            return self.db.query(self.model).filter(self.model.id == id).first()
        except SQLAlchemyError as e:
            raise DatabaseException(f"Error fetching {self.model.__name__}: {str(e)}")

    def get_or_raise(self, id: int, error_message: Optional[str] = None) -> ModelType:
        """
        Get a record by ID or raise NotFoundException.

        Args:
            id: Record ID
            error_message: Custom error message

        Returns:
            Model instance

        Raises:
            NotFoundException: If record not found
        """
        record = self.get(id)
        if not record:
            msg = error_message or f"{self.model.__name__} with ID {id} not found"
            raise NotFoundException(msg)
        return record

    def get_all(
        self, 
        skip: int = 0, 
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
        descending: bool = False
    ) -> List[ModelType]:
        """
        Get all records with pagination and ordering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return (None for no limit)
            order_by: Column name to order by (defaults to 'id')
            descending: Order descending if True

        Returns:
            List of model instances
        """
        try:
            query = self.db.query(self.model)

            # Apply ordering
            if order_by:
                column = getattr(self.model, order_by, self.model.id)
                order_func = desc if descending else asc
                query = query.order_by(order_func(column))
            else:
                query = query.order_by(self.model.id)

            # Apply pagination
            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            raise DatabaseException(f"Error fetching all {self.model.__name__}: {str(e)}")

    def create(self, obj: ModelType, commit: bool = True) -> ModelType:
        """
        Create a new record.

        Args:
            obj: Model instance to create
            commit: Commit the transaction (False only flushes, so the caller
                can make more changes and commit them atomically)

        Returns:
            Created model instance
        """
        try:
            self.db.add(obj)
            self._commit_or_flush(commit)
            self.db.refresh(obj)
            return obj
        except IntegrityError as e:
            self.db.rollback()
            raise ConflictException(f"Conflict creating {self.model.__name__}: {str(e)}")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error creating {self.model.__name__}: {str(e)}")

    def create_from_schema(self, schema: CreateSchemaType, commit: bool = True) -> ModelType:
        """
        Create a new record from Pydantic schema.
        
        Args:
            schema: Pydantic schema with creation data
            
        Returns:
            Created model instance
        """
        # Check if model has from_create_schema method
        if hasattr(self.model, 'from_create_schema'):
            obj = self.model.from_create_schema(schema.model_dump())
        else:
            obj = self.model(**schema.model_dump())

        return self.create(obj, commit)

    def update(self, obj: ModelType, commit: bool = True) -> ModelType:
        """
        Update an existing record.
        
        Args:
            obj: Model instance to update
            commit: Commit the transaction (False only flushes)
            
        Returns:
            Updated model instance
        """
        try:
            self._commit_or_flush(commit)
            self.db.refresh(obj)
            return obj
        except IntegrityError as e:
            self.db.rollback()
            raise ConflictException(f"Conflict updating {self.model.__name__}: {str(e)}")
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error updating {self.model.__name__}: {str(e)}")

    def update_from_schema(self, id: int, schema: UpdateSchemaType, commit: bool = True) -> ModelType:
        """
        Update a record from Pydantic schema.

        Args:
            id: Record ID to update
            schema: Pydantic schema with update data

        Returns:
            Updated model instance
        """
        obj = self.get_or_raise(id)

        # Check if model has update_from_schema method
        if hasattr(obj, 'update_from_schema'):
            obj.update_from_schema(schema.model_dump(exclude_unset=True))
        else:
            update_data = schema.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(obj, key, value)

        return self.update(obj, commit)
    
    def delete(self, id: int, commit: bool = True) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Record ID to delete
            commit: Commit the transaction (False only flushes)

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseException: If database error occurs
        """
        try:
            obj = self.get(id)
            if not obj:
                return False

            self.db.delete(obj)
            self._commit_or_flush(commit)
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error deleting {self.model.__name__}: {str(e)}")
    
    def delete_or_raise(self, id: int, error_message: Optional[str] = None) -> None:
        """
        Delete a record by ID or raise exception.

        Args:
            id: Record ID to delete
            error_message: Custom error message

        Raises:
            NotFoundException: If record not found
        """
        deleted = self.delete(id)
        if not deleted:
            msg = error_message or f"{self.model.__name__} with ID {id} not found"
            raise NotFoundException(msg)

    # =========================================================================
    # QUERY OPERATIONS
    # =========================================================================

    def count(self) -> int:
        """
        Count total number of records.

        Returns:
            Total count
        """
        try:
            return self.db.query(func.count(self.model.id)).scalar()
        except SQLAlchemyError as e:
            raise DatabaseException(f"Error counting {self.model.__name__}: {str(e)}")

    def exists(self, id: int) -> bool:
        """
        Check if a record exists by ID.

        Args:
            id: Record ID to check

        Returns:
            True if exists, False otherwise
        """
        try:
            return self.db.query(
                self.db.query(self.model).filter(self.model.id == id).exists()
            ).scalar()
        except SQLAlchemyError as e:
            raise DatabaseException(f"Error checking existence of {self.model.__name__}: {str(e)}")

    def find_one_by(self, **filters) -> Optional[ModelType]:
        """
        Find a single record matching the filters.

        Args:
            **filters: Keyword arguments for filtering

        Returns:
            Model instance or None
        """
        try:
            return self.db.query(self.model).filter_by(**filters).first()
        except SQLAlchemyError as e:
            raise DatabaseException(f"Error finding {self.model.__name__}: {str(e)}")

    def find_all_by(
        self, 
        skip: int = 0, 
        limit: Optional[int] = None,
        **filters
    ) -> List[ModelType]:
        """
        Find all records matching the filters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return (None for no limit)
            **filters: Keyword arguments for filtering

        Returns:
            List of model instances
        """
        try:
            query = self.db.query(self.model).filter_by(**filters)
            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            raise DatabaseException(f"Error finding all {self.model.__name__}: {str(e)}")

    def search(
        self,
        query_str: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
        skip: int = 0,
        limit: Optional[int] = None,
        **additional_filters
    ) -> List[ModelType]:
        """
        Search records by text in specified fields.

        Args:
            query_str: Search query string
            search_fields: List of field names to search in
            skip: Number of records to skip
            limit: Maximum number of records to return (None for no limit)
            **additional_filters: Additional filter criteria

        Returns:
            List of model instances
        """
        try:
            q = self.db.query(self.model)

            # Apply additional filters
            if additional_filters:
                q = q.filter_by(**additional_filters)

            # Apply text search if provided
            if query_str and search_fields:
                from sqlalchemy import or_
                conditions = []
                for field in search_fields:
                    if hasattr(self.model, field):
                        column = getattr(self.model, field)
                        conditions.append(column.ilike(f"%{query_str}%"))

                if conditions:
                    q = q.filter(or_(*conditions))

            return q.offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            raise DatabaseException(f"Error searching {self.model.__name__}: {str(e)}")

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def refresh(self, obj: ModelType) -> ModelType:
        """
        Refresh a model instance from the database.

        Args:
            obj: Model instance to refresh

        Returns:
            Refreshed model instance
        """
        try:
            self.db.refresh(obj)
            return obj
        except SQLAlchemyError as e:
            raise DatabaseException(f"Error refreshing {self.model.__name__}: {str(e)}")

    def save_changes(self) -> None:
        """
        Commit the current transaction.

        Raises:
            DatabaseException: If commit fails
        """
        try:
            self.db.commit()
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DatabaseException(f"Error saving changes: {str(e)}")

    @contextmanager
    def atomic(self):
        """
        Commit the writes made inside the block (with commit=False) as one
        transaction, or roll all of them back if any of them fails.
        """
        try:
            yield
            self.save_changes()
        except Exception:
            self.rollback()
            raise

    def _commit_or_flush(self, commit: bool) -> None:
        if commit:
            self.db.commit()
        else:
            self.db.flush()

    def rollback(self) -> None:
        """
        Rollback the current transaction.
        """
        self.db.rollback()

    # =========================================================================
    # CONVERSION METHODS
    # =========================================================================

    def to_response(self, obj: ModelType) -> Dict[str, Any]:
        """
        Convert a model instance to response dictionary.

        Args:
            obj: Model instance

        Returns:
            Dictionary representation
        """
        if hasattr(obj, 'to_response'):
            return obj.to_response()

        # Default conversion
        result = {}
        for column in obj.__table__.columns:
            result[column.name] = getattr(obj, column.name)
        return result

    def to_response_list(self, objects: List[ModelType]) -> List[Dict[str, Any]]:
        """
        Convert a list of model instances to response dictionaries.

        Args:
            objects: List of model instances

        Returns:
            List of dictionary representations
        """
        return [self.to_response(obj) for obj in objects]
