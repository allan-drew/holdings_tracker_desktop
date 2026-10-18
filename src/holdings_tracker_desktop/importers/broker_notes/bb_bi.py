import re
from datetime import date, datetime
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
# The 4-char root may contain digits (B3SA3, M1TA34) but ends with a letter
TICKER_RE = re.compile(r"\b([A-Z0-9]{3}[A-Z]\d{1,2})F?\b")
NET_RE = re.compile(rf"L[íi]quido para\s+\d{{2}}/\d{{2}}/\d{{4}}\s+({NUMBER})")
# e.g. "I.R.R.F. s/ operações, base R$ 100.000,00 5,00"; the Day-Trade line has no "s/"
IRRF_LINE_RE = re.compile(r"^[^\n]*I\.R\.R\.F\.?\s*s/\s*opera[^\n]*$", re.MULTILINE)
NUMBER_RE = re.compile(NUMBER)

# Rounding allowed between quantity x price and the trade value printed on the note
VALUE_TOLERANCE = Decimal("0.01")

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
        quantity = parse_br_decimal(trade["quantity"])
        price = parse_br_decimal(trade["price"])
        gross = parse_br_decimal(trade["value"])
        net = parse_br_decimal(self._search(NET_RE, text, "net_value"))
        taxes = self._irrf(text)
        fees = abs(net - gross) - taxes

        self._check_consistency(quantity, price, gross, fees, taxes)

        return ParsedBrokerNote(
            broker_aliases=self.broker_aliases,
            date=self._date(text),
            operation=OperationType.BUY if trade["side"] == "C" else OperationType.SELL,
            note_number=self._search(NOTE_NUMBER_RE, text, "note_number"),
            ticker=self._ticker(trade["spec"]),
            quantity=quantity,
            price=price,
            fees=fees,
            taxes=taxes,
        )

    def _irrf(self, text: str) -> Decimal:
        line = IRRF_LINE_RE.search(text)
        if not line:
            return Decimal("0")

        # The value must follow the label on the same line, after the base when there is one
        label_start = line.group(0).find("I.R.R.F")
        after_label = line.group(0)[label_start:]
        numbers = NUMBER_RE.findall(after_label)
        if len(numbers) < (2 if "base" in after_label.lower() else 1):
            raise self._parse_error("irrf")

        return parse_br_decimal(numbers[-1])

    def _check_consistency(self, quantity, price, gross, fees, taxes):
        # Values read from the wrong place usually break one of these
        if (
            abs(quantity * price - gross) > VALUE_TOLERANCE
            or fees < 0
            or taxes < 0
            or taxes >= gross
        ):
            raise ValidationException(
                f"Inconsistent values in PDF: quantity={quantity} price={price} "
                f"value={gross} fees={fees} taxes={taxes}",
                "error_pdf_inconsistent_values",
            )

    def _date(self, text: str) -> date:
        try:
            return datetime.strptime(self._search(DATE_RE, text, "date"), "%d/%m/%Y").date()
        except ValueError:
            raise self._parse_error("date")

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
