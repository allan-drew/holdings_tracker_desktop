from PySide6.QtWidgets import QDialog

from holdings_tracker_desktop.database import get_db
from holdings_tracker_desktop.services.asset_event_service import AssetEventService
from holdings_tracker_desktop.ui.core import t, global_signals
from holdings_tracker_desktop.ui.core.formatters import format_date
from holdings_tracker_desktop.ui.core.ui_helpers import prepare_table, table_item
from holdings_tracker_desktop.ui.widgets.entity_manager_widget import EntityManagerWidget

class AssetEventsWidget(EntityManagerWidget):
    def __init__(self, asset_id: int, parent=None):
        super().__init__(parent)
        self.asset_id = asset_id

    def get_extra_buttons(self):
        return [("back", "fa5s.arrow-left", self.on_back_clicked)]

    def supports_details(self) -> bool:
        return True

    def load_data(self):
        self.ui_data = []

        try:
            with get_db() as db:
                service = AssetEventService(db)
                self.ui_data = service.list_all_for_ui(asset_id=self.asset_id)

        except Exception as e:
            self.show_load_error(e)
            self.table.setRowCount(0)

        self.translate_ui()

    def translate_ui(self):
        super().translate_ui()
        self.title_widget.set_primary_text(t("events"))
        self.title_widget.set_secondary_text(str(len(self.ui_data)))
        self._populate_table(self.ui_data)

    def on_back_clicked(self):
        from holdings_tracker_desktop.ui.widgets.assets_widget import AssetsWidget
        self.navigate_to(AssetsWidget)

    def open_new_form(self):
        from holdings_tracker_desktop.ui.forms.asset_event_form import AssetEventForm

        form = AssetEventForm(
            asset_id=self.asset_id,
            parent=self
        )

        if form.exec() == QDialog.Accepted:
            self.load_data()
            global_signals.asset_events_updated.emit()

    def open_edit_form(self, selected_id):
        from holdings_tracker_desktop.ui.forms.asset_event_form import AssetEventForm

        try:
            with get_db() as db:
                service = AssetEventService(db)
                asset_event = service.get(selected_id)

                form = AssetEventForm(
                    asset_event_id=selected_id,
                    asset_id=self.asset_id,
                    initial_data={
                        'date': asset_event.date,
                        'event_type': asset_event.event_type,
                        'factor': asset_event.factor,
                        'quantity': asset_event.quantity,
                        'price': asset_event.price,
                        'target_asset_id': asset_event.target_asset_id,
                        'target_quantity': asset_event.target_quantity,
                        'target_unit_price': asset_event.target_unit_price,
                        'residual_value': asset_event.residual_value,
                    },
                    parent=self
                )

                if form.exec() == QDialog.Accepted:
                    self.load_data()
                    global_signals.asset_events_updated.emit()

        except Exception as e:
            self.show_open_form_error(e)

    def delete_record(self, selected_id):
        self.delete_with_confirmation(
            selected_id,
            title=t('delete_asset_event'),
            service_cls=AssetEventService,
            on_deleted=self._on_record_deleted,
        )

    def _on_record_deleted(self):
        self.load_data()
        global_signals.asset_events_updated.emit()

    def open_details(self, selected_id):
        from holdings_tracker_desktop.ui.dialogs.asset_event_details_dialog import (
            AssetEventDetailsDialog
        )

        AssetEventDetailsDialog(
            asset_event_id=selected_id,
            parent=self
        ).exec()

    def _populate_table(self, items):
        prepare_table(self.table, 3, len(items))

        self.table.setHorizontalHeaderLabels([t("asset"), t("date"), t("type")])

        for row, item in enumerate(items):
            self.table.setItem(row, 0, table_item(item['asset_ticker'], item['id']))
            self.table.setItem(row, 1, table_item(format_date(item['date'])))
            self.table.setItem(row, 2, table_item(t(item['event_type'].value.lower())))
