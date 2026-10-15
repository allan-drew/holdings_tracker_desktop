from PySide6.QtWidgets import QDialog, QHeaderView

from holdings_tracker_desktop.database import get_db
from holdings_tracker_desktop.services.currency_service import CurrencyService
from holdings_tracker_desktop.ui.core import t
from holdings_tracker_desktop.ui.core.ui_helpers import prepare_table, table_item
from holdings_tracker_desktop.ui.widgets.entity_manager_widget import EntityManagerWidget

class CurrenciesWidget(EntityManagerWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def supports_details(self) -> bool:
        return True

    def load_data(self):
        self.ui_data = []

        try:
            with get_db() as db:
                service = CurrencyService(db)
                self.ui_data = service.list_all_for_ui()

        except Exception as e:
            self.show_load_error(e)
            self.table.setRowCount(0)

        self.translate_ui()

    def translate_ui(self):
        super().translate_ui()
        self.title_widget.set_primary_text(t("currencies"))
        self.title_widget.set_secondary_text(str(len(self.ui_data)))
        self._populate_table(self.ui_data)

    def open_new_form(self):
        from holdings_tracker_desktop.ui.forms.currency_form import CurrencyForm

        form = CurrencyForm(parent=self)

        if form.exec() == QDialog.Accepted:
            self.load_data()

    def open_edit_form(self, selected_id):
        from holdings_tracker_desktop.ui.forms.currency_form import CurrencyForm

        try:
            with get_db() as db:
                service = CurrencyService(db)
                currency = service.get(selected_id)

                form = CurrencyForm(
                    currency_id=selected_id,
                    initial_data={
                        'code': currency.code,
                        'name': currency.name,
                        'symbol': currency.symbol,
                    },
                    parent=self
                )

                if form.exec() == QDialog.Accepted:
                    self.load_data()

        except Exception as e:
            self.show_open_form_error(e)

    def delete_record(self, selected_id):
        self.delete_with_confirmation(
            selected_id,
            title=t('delete_currency'),
            service_cls=CurrencyService,
            on_deleted=self.load_data,
        )

    def open_details(self, selected_id):
        from holdings_tracker_desktop.ui.dialogs.currency_details_dialog import (
            CurrencyDetailsDialog
        )

        CurrencyDetailsDialog(
            currency_id=selected_id,
            parent=self
        ).exec()

    def _populate_table(self, items):
        prepare_table(self.table, 4, len(items))

        self.table.setHorizontalHeaderLabels([t("code"), t("name"), t("symbol"), t("assets")])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        for row, item in enumerate(items):
            self.table.setItem(row, 0, table_item(item['code'], item['id']))
            self.table.setItem(row, 1, table_item(item['name']))
            self.table.setItem(row, 2, table_item(item['symbol']))
            self.table.setItem(row, 3, table_item(str(item['assets_count'])))
