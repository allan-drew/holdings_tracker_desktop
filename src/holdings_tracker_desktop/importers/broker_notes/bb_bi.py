import re
from datetime import datetime
from decimal import Decimal

from holdings_tracker_desktop.importers.broker_notes.base import (
    BrokerNoteParser, ParsedBrokerNote, parse_br_decimal
)
from holdings_tracker_desktop.models.broker_note import OperationType
from holdings_tracker_desktop.utils.exceptions import ValidationException

CNPJ = "24.933.830/0001-30"

NUMBER = r"\d[\d.]*(?:,\d+)?"

NOTE_NUMBER_RE = re.compile(r"Nr\.Nota[^\n]*\n\s*(\d+/[\d.]+)")
DATE_RE = re.compile(r"Data preg[ãa]o[^\n]*\n[^\n]*?(\d{2}/\d{2}/\d{4})")
# e.g. "1-BOVESPA C VISTA ENGIE BRASIL ON      NM - EGIE3 H 100 30,27 3.027,00 D"
TRADE_RE = re.compile(
    rf"^\s*\S*BOVESPA\s+(?P<side>[CV])\s+(?P<spec>.+?)\s+"
    rf"(?P<quantity>{NUMBER})\s+(?P<price>{NUMBER})\s+(?P<value>{NUMBER})\s+[DC]\s*$",
    re.MULTILINE,
)
TICKER_RE = re.compile(r"\b([A-Z]{4}\d{1,2})F?\b")
NET_RE = re.compile(rf"L[íi]quido para\s+\d{{2}}/\d{{2}}/\d{{4}}\s+({NUMBER})")
IRRF_RE = re.compile(rf"I\.R\.R\.F\.?\s*s/\s*opera[^\n]*?({NUMBER})\s*$", re.MULTILINE)

class BbBiParser(BrokerNoteParser):
    """BB Banco de Investimento (BB-BI) home broker notes."""

    broker_aliases = ("BB-BI", "BB BANCO DE INVESTIMENTO")

    def matches(self, text: str) -> bool:
        return CNPJ in text or "BB BANCO DE INVESTIMENTO" in text.upper()

    def parse(self, text: str) -> ParsedBrokerNote:
        trades = list(TRADE_RE.finditer(text))
        if not trades:
            raise self._parse_error("trades")
        if len(trades) > 1:
            raise ValidationException(
                "Only notes with a single trade can be imported", "error_pdf_multiple_assets"
            )

        trade = trades[0]
        gross = parse_br_decimal(trade["value"])
        net = parse_br_decimal(self._search(NET_RE, text, "net_value"))

        irrf_match = IRRF_RE.search(text)
        taxes = parse_br_decimal(irrf_match.group(1)) if irrf_match else Decimal("0")

        return ParsedBrokerNote(
            broker_aliases=self.broker_aliases,
            date=datetime.strptime(self._search(DATE_RE, text, "date"), "%d/%m/%Y").date(),
            operation=OperationType.BUY if trade["side"] == "C" else OperationType.SELL,
            note_number=self._search(NOTE_NUMBER_RE, text, "note_number"),
            ticker=self._ticker(trade["spec"]),
            quantity=parse_br_decimal(trade["quantity"]),
            price=parse_br_decimal(trade["price"]),
            fees=abs(net - gross) - taxes,
            taxes=taxes,
        )

    def _ticker(self, spec: str) -> str:
        # The ticker is the last code in the specification ("ENGIE BRASIL ON NM - EGIE3");
        # fractional market tickers end with "F" (EGIE3F), which is dropped.
        tickers = TICKER_RE.findall(spec)
        if not tickers:
            raise self._parse_error("asset")
        return tickers[-1]

    def _search(self, pattern: re.Pattern, text: str, field: str) -> str:
        match = pattern.search(text)
        if not match:
            raise self._parse_error(field)
        return match.group(1)

    def _parse_error(self, field: str) -> ValidationException:
        return ValidationException(
            f"Could not read '{field}' from the PDF", "error_pdf_parse_failed", field=field
        )
