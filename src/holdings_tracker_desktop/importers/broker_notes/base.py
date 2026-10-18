from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from holdings_tracker_desktop.models.broker_note import OperationType
from holdings_tracker_desktop.utils.exceptions import ValidationException

@dataclass(frozen=True)
class ParsedBrokerNote:
    """Broker note data read from a PDF, still referencing broker and asset by name."""
    broker_aliases: tuple[str, ...]
    date: date
    operation: OperationType
    note_number: str | None
    ticker: str
    quantity: Decimal
    price: Decimal
    fees: Decimal
    taxes: Decimal

class BrokerNoteParser(ABC):
    """Reads the text of one broker's note layout."""

    # Substrings that identify the broker among the registered broker names
    broker_aliases: tuple[str, ...] = ()

    @abstractmethod
    def matches(self, text: str) -> bool:
        """Whether the text comes from a note of this broker."""

    @abstractmethod
    def parse(self, text: str) -> ParsedBrokerNote:
        """Extract the note data, raising ValidationException when it can't."""

def parse_br_decimal(value: str) -> Decimal:
    """Parse a Brazilian formatted number, e.g. '3.027,90' -> Decimal('3027.90')."""
    try:
        return Decimal(value.strip().replace(".", "").replace(",", "."))
    except InvalidOperation:
        raise ValidationException(
            f"Invalid number in PDF: {value!r}", "error_pdf_parse_failed", field=value
        )
