from datetime import date
from decimal import Decimal

import pypdf
import pytest

from holdings_tracker_desktop.importers.broker_notes import (
    extract_pdf_text, parse_broker_note_pdf, parse_broker_note_text
)
from holdings_tracker_desktop.importers.broker_notes.base import parse_br_decimal
from holdings_tracker_desktop.importers.broker_notes.bb_bi import BbBiParser
from holdings_tracker_desktop.models.broker_note import OperationType
from holdings_tracker_desktop.utils.exceptions import ValidationException

# Fictitious data laid out like pypdf's extraction of a real BB-BI note: labels and
# values are often split across lines or appear in a different order.
HEADER = """ Nr.Nota  Folha
12345678/1.234
 Data pregão
1 15/03/2026

 C.N.P.J.:  24.933.830/0001-30 Carta Patente: 9.927.802/87
 Agência  Conta Corrente  Acionista  Administrador  Complemento nome  P.
 BB BANCO DE INVESTIMENTO S.A.
 NOTA DE CORRETAGEM
 Negócios realizados
 | D
Q  Negociação C/V  Tipo mercado  Prazo  Especificação do título  Obs.  Quantidade  Preço / D/C Valor Operação /
"""

BUY_TRADE = "1-BOVESPA C VISTA WEG ON      NM - WEGE3 H 200 40,50 8.100,00 D\nD\nD\n"
SELL_TRADE = "1-BOVESPA V VISTA WEG ON      NM - WEGE3 H 1.000 40,00 40.000,00 C\nD\n"

BUY_FOOTER = """ Resumo dos Negócios
 Compras à vista 8.100,00
 Valor das operações
0,00
8.100,00
 I.R.R.F Day-Trade: Base R$ 0,00             Projeção R$ 0,00
 Resumo Financeiro
 CBLC
8.100,00 Valor líquido das operações
 Taxa de liquidação
 Taxa de Registro
2,03
 Total  CBLC 8.102,03
 Emolumentos 0,40
 Total Bovespa / Soma 0,40
 Total corretagem / Despesas
0,00
 Líquido para  17/03/2026 8.102,43
Página 1 de 1 17/03/2026  11:38
"""

def sell_footer(irrf_line: str) -> str:
    return f""" Resumo Financeiro
40.000,00 Valor líquido das operações
 Total  CBLC 39.990,00
{irrf_line}
 Líquido para  17/03/2026 39.986,00
"""

def test_parses_buy_note_in_real_layout():
    note = parse_broker_note_text(HEADER + BUY_TRADE + BUY_FOOTER)

    assert note.date == date(2026, 3, 15)
    assert note.operation == OperationType.BUY
    assert note.note_number == "12345678/1.234"
    assert note.ticker == "WEGE3"
    assert note.quantity == Decimal("200")
    assert note.price == Decimal("40.50")
    assert note.fees == Decimal("2.43")
    assert note.taxes == Decimal("0")
    assert "BB-BI" in note.broker_aliases

def test_parses_sell_note_with_irrf_as_taxes():
    text = HEADER + SELL_TRADE + sell_footer(" I.R.R.F. s/ operações, base R$ 40.000,00 2,00")
    note = parse_broker_note_text(text)

    assert note.operation == OperationType.SELL
    assert note.quantity == Decimal("1000")
    assert note.taxes == Decimal("2.00")
    assert note.fees == Decimal("12.00")

@pytest.mark.parametrize("irrf_line", [
    " I.R.R.F. s/ operações, base R$ 40.000,00\n2,00",
    "2,00 I.R.R.F. s/ operações, base R$ 40.000,00",
    " I.R.R.F. s/ operações\n2,00",
])
def test_rejects_irrf_value_away_from_its_label(irrf_line):
    with pytest.raises(ValidationException) as exc:
        parse_broker_note_text(HEADER + SELL_TRADE + sell_footer(irrf_line))

    assert exc.value.key == "error_pdf_parse_failed"
    assert exc.value.params == {"field": "irrf"}

def test_rejects_trade_value_that_does_not_match_quantity_times_price():
    trade = "1-BOVESPA C VISTA WEG ON      NM - WEGE3 H 200 40,50 9.100,00 D\n"

    with pytest.raises(ValidationException) as exc:
        parse_broker_note_text(HEADER + trade + BUY_FOOTER)

    assert exc.value.key == "error_pdf_inconsistent_values"

def test_rejects_irrf_larger_than_the_costs():
    text = HEADER + SELL_TRADE + sell_footer(" I.R.R.F. s/ operações, base R$ 40.000,00 20,00")

    with pytest.raises(ValidationException) as exc:
        parse_broker_note_text(text)

    assert exc.value.key == "error_pdf_inconsistent_values"

def test_rejects_note_with_more_than_one_trade():
    with pytest.raises(ValidationException) as exc:
        parse_broker_note_text(HEADER + BUY_TRADE + BUY_TRADE + BUY_FOOTER)

    assert exc.value.key == "error_pdf_multiple_assets"

def test_reports_missing_field():
    with pytest.raises(ValidationException) as exc:
        parse_broker_note_text(HEADER + BUY_TRADE)

    assert exc.value.key == "error_pdf_parse_failed"
    assert exc.value.params == {"field": "net_value"}

def test_reports_invalid_trade_date():
    text = (HEADER + BUY_TRADE + BUY_FOOTER).replace("1 15/03/2026", "1 31/02/2026")

    with pytest.raises(ValidationException) as exc:
        parse_broker_note_text(text)

    assert exc.value.params == {"field": "date"}

@pytest.mark.parametrize("spec, ticker", [
    ("VISTA WEG ON      NM - WEGE3 H", "WEGE3"),
    ("VISTA B3 ON NM - B3SA3 #", "B3SA3"),
    ("VISTA META PLATDRN - M1TA34 2", "M1TA34"),
    ("VISTA APPLE DRN - AAPL34", "AAPL34"),
    ("VISTA TAESA UNT N2 - TAEE11 H", "TAEE11"),
    ("FRACIONARIO FII VINCI SC  CI ER - VISC11F H", "VISC11"),
])
def test_extracts_ticker(spec, ticker):
    assert BbBiParser()._ticker(spec) == ticker

def test_matches_by_cnpj_or_name_only():
    parser = BbBiParser()

    assert parser.matches("C.N.P.J.:  24.933.830/0001-30")
    assert parser.matches("Bb Banco de Investimento S.A.")
    assert not parser.matches("NOTA DE CORRETAGEM\nOUTRA CORRETORA S.A.")

def test_rejects_unknown_broker():
    with pytest.raises(ValidationException) as exc:
        parse_broker_note_text("NOTA DE CORRETAGEM\nOUTRA CORRETORA S.A.")

    assert exc.value.key == "error_pdf_unsupported_broker"

def test_reports_file_that_is_not_a_pdf(tmp_path):
    path = tmp_path / "note.pdf"
    path.write_text("not a pdf")

    with pytest.raises(ValidationException) as exc:
        parse_broker_note_pdf(str(path))

    assert exc.value.key == "error_pdf_unreadable"

def test_reports_unexpected_pypdf_errors_as_unreadable(monkeypatch):
    def broken_reader(path):
        raise TypeError("damaged object stream")

    monkeypatch.setattr(pypdf, "PdfReader", broken_reader)

    with pytest.raises(ValidationException) as exc:
        extract_pdf_text("note.pdf")

    assert exc.value.key == "error_pdf_unreadable"

@pytest.mark.parametrize("text, expected", [
    ("3.027,90", Decimal("3027.90")),
    ("100", Decimal("100")),
    ("0,15", Decimal("0.15")),
])
def test_parse_br_decimal(text, expected):
    assert parse_br_decimal(text) == expected
