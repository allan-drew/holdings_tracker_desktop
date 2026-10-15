from datetime import date
from decimal import Decimal

from holdings_tracker_desktop.ui.core.formatters import format_date, format_quantity
from holdings_tracker_desktop.ui.core.translations import t
from holdings_tracker_desktop.utils.exceptions import AppException

def error_text(error: Exception) -> str:
    """User-facing text for an exception, translated when it carries a key."""
    if isinstance(error, AppException) and error.key:
        params = {name: _format_param(value) for name, value in error.params.items()}

        try:
            return t(error.key).format(**params)
        except (KeyError, IndexError, ValueError):
            # Translation and params out of sync: show the English message instead of failing
            return error.message

    return str(error)

def _format_param(value):
    if isinstance(value, Decimal):
        return format_quantity(value)

    if isinstance(value, date):
        return format_date(value)

    return value
