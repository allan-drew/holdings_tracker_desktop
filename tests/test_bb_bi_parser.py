from datetime import date
from decimal import Decimal

import pytest

from holdings_tracker_desktop.importers.broker_notes import parse_broker_note_text
from holdings_tracker_desktop.importers.broker_notes.base import parse_br_decimal
from holdings_tracker_desktop.importers.broker_notes.bb_bi import BbBiParser
from holdings_tracker_desktop.models.broker_note import OperationType
from holdings_tracker_desktop.utils.exceptions import ValidationException

# Shaped like pypdf's extraction of a BB-BI note, without personal data.
HEADER = """ Nr.Nota  Folha
22092026/2.797
 Data pregão
1 22/09/2026
 C.N.P.J.:  24.933.830/0001-30 Carta Patente: 9.927.802/87
 BB BANCO DE INVESTIMENTO S.A.
Q  Negociação C/V  Tipo mercado  Prazo  Especificação do título  Obs.  Quantidade  Preço / D/C Valor Operação /
"""

BUY_TRADE = "1-BOVESPA C VISTA ENGIE BRASIL ON      NM - EGIE3 H 100 30,27 3.027,00 D\n"
SELL_TRADE = "1-BOVESPA V FRACIONARIO FII VINCI SC  CI ER - VISC11F H 1.000 100,00 100.000,00 C\n"

BUY_FOOTER = """ Resumo Financeiro
 I.R.R.F Day-Trade: Base R$ 0,00             Projeção R$ 0,00
 Emolumentos 0,15
 Líquido para  24/09/2026 3.027,90
"""

SELL_FOOTER = """ Resumo Financeiro
 I.R.R.F. s/ operações, base R$ 100.000,00 5,00
 Líquido para  24/09/2026 99.965,00
"""

def test_parses_buy_note():
    note = parse_broker_note_text(HEADER + BUY_TRADE + BUY_FOOTER)

    assert note.date == date(2026, 9, 22)
    assert note.operation == OperationType.BUY
    assert note.note_number == "22092026/2.797"
    assert note.ticker == "EGIE3"
    assert note.quantity == Decimal("100")
    assert note.price == Decimal("30.27")
    assert note.fees == Decimal("0.90")
    assert note.taxes == Decimal("0")
    assert "BB-BI" in note.broker_aliases

def test_parses_sell_note_with_irrf_as_taxes():
    note = parse_broker_note_text(HEADER + SELL_TRADE + SELL_FOOTER)

    assert note.operation == OperationType.SELL
    assert note.ticker == "VISC11"
    assert note.quantity == Decimal("1000")
    assert note.price == Decimal("100.00")
    assert note.taxes == Decimal("5.00")
    assert note.fees == Decimal("30.00")

def test_rejects_note_with_more_than_one_trade():
    with pytest.raises(ValidationException) as exc:
        parse_broker_note_text(HEADER + BUY_TRADE + BUY_TRADE + BUY_FOOTER)

    assert exc.value.key == "error_pdf_multiple_assets"

def test_reports_missing_field():
    with pytest.raises(ValidationException) as exc:
        parse_broker_note_text(HEADER + BUY_TRADE)

    assert exc.value.key == "error_pdf_parse_failed"
    assert exc.value.params == {"field": "net_value"}

def test_rejects_unknown_broker():
    assert not BbBiParser().matches("NOTA DE CORRETAGEM\nOUTRA CORRETORA S.A.")

    with pytest.raises(ValidationException) as exc:
        parse_broker_note_text("NOTA DE CORRETAGEM\nOUTRA CORRETORA S.A.")

    assert exc.value.key == "error_pdf_unsupported_broker"

@pytest.mark.parametrize("text, expected", [
    ("3.027,90", Decimal("3027.90")),
    ("100", Decimal("100")),
    ("0,15", Decimal("0.15")),
])
def test_parse_br_decimal(text, expected):
    assert parse_br_decimal(text) == expected
