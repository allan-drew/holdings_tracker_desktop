from holdings_tracker_desktop.ui.core import t
from holdings_tracker_desktop.ui.core.formatters import format_date, format_datetime, format_decimal, format_quantity
from holdings_tracker_desktop.ui.dialogs.base_details_dialog import BaseDetailsDialog

class BrokerNoteDetailsDialog(BaseDetailsDialog):
    def __init__(self, broker_note_id: int, parent=None):
        self.broker_note_id = broker_note_id
        super().__init__(parent)

        self._load_data()
        self.setWindowTitle(t("broker_note_details"))

    def _load_data(self):
        from holdings_tracker_desktop.database import get_db
        from holdings_tracker_desktop.services.broker_note_service import BrokerNoteService

        with get_db() as db:
            service = BrokerNoteService(db)
            note = service.get_details(self.broker_note_id)

            self.add_detail(t("date"), format_date(note.date))
            self.add_detail(t("operation"), t(note.operation.value.lower()))
            self.add_detail(t("broker"), note.broker.name)
            self.add_detail(t("asset"), note.asset.ticker)
            self.add_detail(t("quantity"), format_quantity(note.quantity))
            self.add_detail(t("price"), format_decimal(note.price))
            self.add_detail(t("fees"), format_decimal(note.fees))
            self.add_detail(t("taxes"), format_decimal(note.taxes))
            self.add_detail(t("total_value"), format_decimal(note.total_value))
            self.add_detail(t("created_at"), format_datetime(note.created_at_local))
            self.add_detail(t("updated_at"), format_datetime(note.updated_at_local))

            if note.note_number:
                self.add_detail(t("note_number"), str(note.note_number))
