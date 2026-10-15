from PySide6.QtWidgets import QDialog, QHeaderView

from holdings_tracker_desktop.database import get_db
from holdings_tracker_desktop.models.broker_note import OperationType
from holdings_tracker_desktop.services.broker_note_service import BrokerNoteService
from holdings_tracker_desktop.ui.comboboxes import BrokerNoteYearComboBox
from holdings_tracker_desktop.ui.core import t, global_signals
from holdings_tracker_desktop.ui.core.formatters import format_date
from holdings_tracker_desktop.ui.core.ui_helpers import prepare_table, table_item, decimal_table_item, quantity_table_item
from holdings_tracker_desktop.ui.widgets.entity_manager_widget import EntityManagerWidget

class BrokerNotesWidget(EntityManagerWidget):
    RECORD_LABEL_COLUMNS = (0, 1, 2)

    """
    BrokerNotes UI update flow (by year filter):

        CRUD BrokerNote
            ↓
        global_signals.broker_notes_updated
            ↓
        BrokerNoteYearComboBox.reload()
            ↓
        setCurrentIndex(...)
            ↓
        currentIndexChanged
            ↓
        BrokerNotesWidget.load_data()
            ↓
        _populate_table()

    Notes:
    - The ComboBox is the single source of truth for filtering.
    - This widget never calls load_data() directly after CRUD.
    - Table reloads only in response to filter changes.
    """

    def __init__(self, parent=None):
        self.year_filter = BrokerNoteYearComboBox()
        self.year_filter.currentIndexChanged.connect(self.load_data)

        super().__init__(parent)

    def get_toolbar_filters(self):
        return [self.year_filter]

    def supports_details(self) -> bool:
        return True

    def load_data(self):
        self.ui_data = []

        try:
            with get_db() as db:
                service = BrokerNoteService(db)
                year = self.year_filter.currentData()

                if year is not None:
                    self.ui_data = service.list_by_year_for_ui(year)

        except Exception as e:
            self.show_load_error(e)
            self.table.setRowCount(0)

        self.translate_ui()

    def translate_ui(self):
        super().translate_ui()
        self.title_widget.set_primary_text(t("broker_notes"))
        self.title_widget.set_secondary_text(str(len(self.ui_data)))
        self.year_filter.translate_placeholder()
        self._populate_table(self.ui_data)

    def open_new_form(self):
        from holdings_tracker_desktop.ui.forms.broker_note_form import BrokerNoteForm

        form = BrokerNoteForm(parent=self)

        if form.exec() == QDialog.Accepted:
            global_signals.broker_notes_updated.emit()

    def open_edit_form(self, selected_id):
        from holdings_tracker_desktop.ui.forms.broker_note_form import BrokerNoteForm

        try:
            with get_db() as db:
                service = BrokerNoteService(db)
                broker_note = service.get(selected_id)

                form = BrokerNoteForm(
                    broker_note_id=selected_id,
                    initial_data={
                        'date': broker_note.date,
                        'operation': broker_note.operation,
                        'broker_id': broker_note.broker_id,
                        'asset_id': broker_note.asset_id,
                        'quantity': broker_note.quantity,
                        'price': broker_note.price,
                        'fees': broker_note.fees,
                        'taxes': broker_note.taxes,
                        'note_number': broker_note.note_number
                    },
                    parent=self
                )

                if form.exec() == QDialog.Accepted:
                    global_signals.broker_notes_updated.emit()

        except Exception as e:
            self.show_open_form_error(e)

    def delete_record(self, selected_id):
        self.delete_with_confirmation(
            selected_id,
            title=t('delete_broker_note'),
            service_cls=BrokerNoteService,
            on_deleted=global_signals.broker_notes_updated.emit,
        )

    def open_details(self, selected_id):
        from holdings_tracker_desktop.ui.dialogs.broker_note_details_dialog import (
            BrokerNoteDetailsDialog
        )

        BrokerNoteDetailsDialog(
            broker_note_id=selected_id,
            parent=self
        ).exec()

    def _populate_table(self, items):
        prepare_table(self.table, 7, len(items))

        self.table.setHorizontalHeaderLabels(
            [t("date"), t("operation_abbr"), t("asset"), t("quantity_abbr"), 
             t("price"), t("fees"), t("total_value")]
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        for row, item in enumerate(items):
            self.table.setItem(row, 0, table_item(format_date(item['date']), item['id']))
            self.table.setItem(row, 1, table_item(t(item['operation'].value.lower())))
            self.table.setItem(row, 2, table_item(item['asset_ticker']))
            self.table.setItem(row, 3, quantity_table_item(item['quantity']))
            currency = item.get("asset_currency", "")
            self.table.setItem(row, 4, decimal_table_item(item['price'], 2, currency))
            self.table.setItem(row, 5, decimal_table_item(item['fees'], 2, currency))
            self.table.setItem(row, 6, decimal_table_item(item['total_value'], 2, currency))

        year = self.year_filter.currentData()
        if year is None:
            return

        # Buys and sells are totaled separately: their sum has no meaning.
        for operation in OperationType:
            operation_items = [item for item in items if item['operation'] == operation]
            if not operation_items:
                continue

            self.add_grouped_total_rows(
                operation_items,
                group_by_key="asset_currency",
                value_key="total_value",
                value_column=6,
                label_column=0,
                label_text=t(f"total_{operation.value.lower()}"),
                decimals=2,
                currency_key="asset_currency",
            )
