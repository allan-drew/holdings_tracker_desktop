from PySide6.QtWidgets import QDialog

from holdings_tracker_desktop.database import get_db
from holdings_tracker_desktop.services.asset_ticker_history_service import AssetTickerHistoryService
from holdings_tracker_desktop.ui.core import t, global_signals
from holdings_tracker_desktop.ui.core.formatters import format_date
from holdings_tracker_desktop.ui.core.ui_helpers import prepare_table, table_item
from holdings_tracker_desktop.ui.widgets.entity_manager_widget import EntityManagerWidget

class AssetTickerHistoriesWidget(EntityManagerWidget):
    def __init__(self, asset_id: int, parent=None):
        super().__init__(parent)
        self.asset_id = asset_id

    def get_enabled_actions(self):
        return ("add", "delete")

    def get_extra_buttons(self):
        return [("back", "fa5s.arrow-left", self.on_back_clicked)]

    def supports_details(self) -> bool:
        return True

    def load_data(self):
        self.ui_data = []

        try:
            with get_db() as db:
                service = AssetTickerHistoryService(db)
                self.ui_data = service.list_all_for_ui(asset_id=self.asset_id)

        except Exception as e:
            self.show_load_error(e)
            self.table.setRowCount(0)

        self.translate_ui()

    def translate_ui(self):
        super().translate_ui()
        self.title_widget.set_primary_text(t("asset_ticker_history"))
        self.title_widget.set_secondary_text(str(len(self.ui_data)))
        self._populate_table(self.ui_data)

    def on_back_clicked(self):
        from holdings_tracker_desktop.ui.widgets.assets_widget import AssetsWidget
        self.navigate_to(AssetsWidget)

    def open_new_form(self):
        from holdings_tracker_desktop.ui.forms.asset_ticker_history_form import AssetTickerHistoryForm

        form = AssetTickerHistoryForm(
            asset_id=self.asset_id,
            parent=self
        )

        if form.exec() == QDialog.Accepted:
            self.load_data()
            global_signals.assets_updated.emit()

    def delete_record(self, selected_id):
        self.delete_with_confirmation(
            selected_id,
            title=t('delete_asset_ticker_history'),
            service_cls=AssetTickerHistoryService,
            on_deleted=self._on_record_deleted,
        )

    def _on_record_deleted(self):
        self.load_data()
        global_signals.assets_updated.emit()

    def open_details(self, selected_id):
        from holdings_tracker_desktop.ui.dialogs.ticker_history_details_dialog import (
            TickerHistoryDetailsDialog
        )

        TickerHistoryDetailsDialog(
            asset_ticker_history_id=selected_id,
            parent=self
        ).exec()

    def _populate_table(self, items):
        prepare_table(self.table, 4, len(items))

        self.table.setHorizontalHeaderLabels(
            [t("asset"), t("change_date"), t("old_ticker"), t("new_ticker")]
        )

        for row, item in enumerate(items):
            self.table.setItem(row, 0, table_item(item['asset_ticker'], item['id']))
            self.table.setItem(row, 1, table_item(format_date(item['change_date'])))
            self.table.setItem(row, 2, table_item(item['old_ticker']))
            self.table.setItem(row, 3, table_item(item['new_ticker']))
