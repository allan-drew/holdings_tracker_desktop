from PySide6.QtWidgets import QDialog, QHeaderView

from holdings_tracker_desktop.database import get_db
from holdings_tracker_desktop.services.asset_service import AssetService
from holdings_tracker_desktop.ui.comboboxes import AssetTypeComboBox
from holdings_tracker_desktop.ui.core import t, global_signals
from holdings_tracker_desktop.ui.core.ui_helpers import prepare_table, table_item
from holdings_tracker_desktop.ui.widgets.entity_manager_widget import EntityManagerWidget

class AssetsWidget(EntityManagerWidget):
    def __init__(self, parent=None):
        self._setup_filters()

        super().__init__(parent)

    def get_extra_buttons(self):
        return [
            ("ticker_change", "fa5s.history", self.on_ticker_change_clicked),
            ("events", "fa5s.exchange-alt", self.on_event_clicked),
        ]

    def get_toolbar_filters(self):
        return [self.asset_type_filter] if self.asset_type_filter else []

    def supports_details(self) -> bool:
        return True

    def load_data(self):
        self.ui_data = []

        try:
            with get_db() as db:
                service = AssetService(db)
                asset_type_id = self.asset_type_filter.currentData() if self.asset_type_filter else None
                self.ui_data = service.list_all_for_ui(asset_type_id=asset_type_id)

        except Exception as e:
            self.show_load_error(e)
            self.table.setRowCount(0)

        self.translate_ui()

    def translate_ui(self):
        super().translate_ui()
        self.title_widget.set_primary_text(t("assets"))
        self.title_widget.set_secondary_text(str(len(self.ui_data)))

        if self.asset_type_filter:
            self.asset_type_filter.translate_placeholder()

        self._populate_table(self.ui_data)

    def open_new_form(self):
        from holdings_tracker_desktop.ui.forms.asset_form import AssetForm

        form = AssetForm(parent=self)

        if form.exec() == QDialog.Accepted:
            self.load_data()
            global_signals.assets_updated.emit()

    def open_edit_form(self, selected_id):
        from holdings_tracker_desktop.ui.forms.asset_form import AssetForm

        try:
            with get_db() as db:
                service = AssetService(db)
                asset = service.get(selected_id)

                form = AssetForm(
                    asset_id=selected_id,
                    initial_data={
                        'ticker': asset.ticker,
                        'type_id': asset.type_id,
                        'currency_id': asset.currency_id,
                        'sector_id': asset.sector_id
                    },
                    parent=self
                )

                if form.exec() == QDialog.Accepted:
                    self.load_data()
                    global_signals.assets_updated.emit()

        except Exception as e:
            self.show_open_form_error(e)

    def delete_record(self, selected_id):
        self.delete_with_confirmation(
            selected_id,
            title=t('delete_asset'),
            service_cls=AssetService,
            on_deleted=self._on_record_deleted,
        )

    def _on_record_deleted(self):
        self.load_data()
        global_signals.assets_updated.emit()

    def open_details(self, selected_id):
        from holdings_tracker_desktop.ui.dialogs.asset_details_dialog import (
            AssetDetailsDialog
        )

        AssetDetailsDialog(
            asset_id=selected_id,
            parent=self
        ).exec()

    def on_ticker_change_clicked(self):
        from holdings_tracker_desktop.ui.widgets.asset_ticker_histories_widget import AssetTickerHistoriesWidget
        self._navigate_from_selected_asset(AssetTickerHistoriesWidget)

    def on_event_clicked(self):
        from holdings_tracker_desktop.ui.widgets.asset_events_widget import AssetEventsWidget
        self._navigate_from_selected_asset(AssetEventsWidget)

    def _navigate_from_selected_asset(self, widget_cls):
        asset_id = self.get_selected_id()
        if not asset_id:
            return

        self.navigate_to(widget_cls, asset_id)

    def _setup_filters(self):
        self.asset_type_filter = AssetTypeComboBox(placeholder_key="all")
        self.asset_type_filter.setObjectName("FilterComboBox")
        self.asset_type_filter.currentIndexChanged.connect(self.load_data)

    def _populate_table(self, items):
        prepare_table(self.table, columns=4, rows=len(items))

        self.table.setHorizontalHeaderLabels([t("ticker"), t("type"), t("currency"), t("sector")])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        for row, item in enumerate(items):
            self.table.setItem(row, 0, table_item(item['ticker'], item['id']))
            self.table.setItem(row, 1, table_item(item['type_name']))
            self.table.setItem(row, 2, table_item(item['currency_code']))
            self.table.setItem(row, 3, table_item(item['sector_name']))
