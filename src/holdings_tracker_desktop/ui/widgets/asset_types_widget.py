from PySide6.QtWidgets import QDialog, QHeaderView

from holdings_tracker_desktop.database import get_db
from holdings_tracker_desktop.services.asset_type_service import AssetTypeService
from holdings_tracker_desktop.ui.core import t, global_signals
from holdings_tracker_desktop.ui.core.ui_helpers import prepare_table, table_item
from holdings_tracker_desktop.ui.widgets.entity_manager_widget import EntityManagerWidget

class AssetTypesWidget(EntityManagerWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def supports_details(self) -> bool:
        return True

    def load_data(self):
        self.ui_data = []

        try:
            with get_db() as db:
                service = AssetTypeService(db)
                self.ui_data = service.list_all_for_ui()

        except Exception as e:
            self.show_load_error(e)
            self.table.setRowCount(0)

        self.translate_ui()

    def translate_ui(self):
        super().translate_ui()
        self.title_widget.set_primary_text(t("asset_types"))
        self.title_widget.set_secondary_text(str(len(self.ui_data)))
        self._populate_table(self.ui_data)

    def open_new_form(self):
        from holdings_tracker_desktop.ui.forms.asset_type_form import AssetTypeForm

        form = AssetTypeForm(parent=self)

        if form.exec() == QDialog.Accepted:
            self.load_data()
            global_signals.asset_types_updated.emit()

    def open_edit_form(self, selected_id):
        from holdings_tracker_desktop.ui.forms.asset_type_form import AssetTypeForm

        try:
            with get_db() as db:
                service = AssetTypeService(db)
                asset_type = service.get(selected_id)

                form = AssetTypeForm(
                    asset_type_id=selected_id,
                    initial_data={
                        'name': asset_type.name,
                        'country_id': asset_type.country_id
                    },
                    parent=self
                )

                if form.exec() == QDialog.Accepted:
                    self.load_data()
                    global_signals.asset_types_updated.emit()

        except Exception as e:
            self.show_open_form_error(e)

    def delete_record(self, selected_id):
        self.delete_with_confirmation(
            selected_id,
            title=t('delete_asset_type'),
            service_cls=AssetTypeService,
            on_deleted=self._on_record_deleted,
        )

    def _on_record_deleted(self):
        self.load_data()
        global_signals.asset_types_updated.emit()

    def open_details(self, selected_id):
        from holdings_tracker_desktop.ui.dialogs.asset_type_details_dialog import (
            AssetTypeDetailsDialog
        )

        AssetTypeDetailsDialog(
            asset_type_id=selected_id,
            parent=self
        ).exec()

    def _populate_table(self, items):
        prepare_table(self.table, 4, len(items))

        self.table.setHorizontalHeaderLabels([t("name"), t("country"), t("assets"), t("asset_sectors")])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        for row, item in enumerate(items):
            self.table.setItem(row, 0, table_item(item['name'], item['id']))
            self.table.setItem(row, 1, table_item(item['country_name'], None))
            self.table.setItem(row, 2, table_item(str(item['assets_count'])))
            self.table.setItem(row, 3, table_item(str(item['sectors_count'])))
