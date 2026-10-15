class AppException(Exception):
    """
    Base exception for the application.

    `message` is the English text for logs and fallback display. When `key` is
    set, the UI shows the translation of `key` formatted with `params` instead.
    """
    def __init__(self, message: str, key: str | None = None, **params):
        self.message = message
        self.key = key
        self.params = params
        super().__init__(self.message)

class NotFoundException(AppException):
    """Raised when a resource is not found"""
    def __init__(self, message: str = "Resource not found", key: str | None = "error_record_not_found", **params):
        super().__init__(message, key, **params)

class ConflictException(AppException):
    """Raised when there's a conflict (e.g., duplicate)"""
    def __init__(self, message: str = "Conflict occurred", key: str | None = None, **params):
        super().__init__(message, key, **params)

class ValidationException(AppException):
    """Raised when validation fails"""
    def __init__(self, message: str = "Validation failed", key: str | None = None, **params):
        super().__init__(message, key, **params)

class DatabaseException(AppException):
    """Raised when a database error occurs"""
    def __init__(self, message: str = "Database error", key: str | None = None, **params):
        super().__init__(message, key, **params)
