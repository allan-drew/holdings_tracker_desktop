from holdings_tracker_desktop.importers.broker_notes.base import BrokerNoteParser, ParsedBrokerNote
from holdings_tracker_desktop.importers.broker_notes.bb_bi import BbBiParser
from holdings_tracker_desktop.utils.exceptions import ValidationException

# One parser per broker layout; the first one whose matches() accepts the text is used.
PARSERS: list[BrokerNoteParser] = [BbBiParser()]

def extract_pdf_text(path: str) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        # pypdf raises plain ValueError, TypeError, etc. on damaged files, not only PyPdfError
        raise ValidationException(f"Could not read the PDF: {e!r}", "error_pdf_unreadable")

def parse_broker_note_text(text: str) -> ParsedBrokerNote:
    for parser in PARSERS:
        if parser.matches(text):
            return parser.parse(text)

    raise ValidationException(
        "No parser supports this broker note", "error_pdf_unsupported_broker"
    )

def parse_broker_note_pdf(path: str) -> ParsedBrokerNote:
    return parse_broker_note_text(extract_pdf_text(path))

__all__ = [
    "ParsedBrokerNote", "BrokerNoteParser", "PARSERS",
    "extract_pdf_text", "parse_broker_note_text", "parse_broker_note_pdf",
]
