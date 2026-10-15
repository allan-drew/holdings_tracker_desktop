from PySide6.QtWidgets import QDialog, QHeaderView

from holdings_tracker_desktop.database import get_db
from holdings_tracker_desktop.services.asset_sector_service import AssetSectorService
from holdings_tracker_desktop.ui.core import t
from holdings_tracker_desktop.ui.core.ui_helpers import prepare_table, table_item
from holdings_tracker_desktop.ui.widgets.entity_manager_widget import EntityManagerWidget

class AssetSectorsWidget(EntityManagerWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def supports_details(self) -> bool:
        return True

    def load_data(self):
        self.ui_data = []

        try:
            with get_db() as db:
                service = AssetSectorService(db)
                self.ui_data = service.list_all_for_ui()

        except Exception as e:
            self.show_load_error(e)
            self.table.setRowCount(0)

        self.translate_ui()

    def translate_ui(self):
        super().translate_ui()
        self.title_widget.set_primary_text(t("asset_sectors"))
        self.title_widget.set_secondary_text(str(len(self.ui_data)))
        self._populate_table(self.ui_data)

    def open_new_form(self):
        from holdings_tracker_desktop.ui.forms.asset_sector_form import AssetSectorForm

        form = AssetSectorForm(parent=self)

        if form.exec() == QDialog.Accepted:
            self.load_data()

    def open_edit_form(self, selected_id):
        from holdings_tracker_desktop.ui.forms.asset_sector_form import AssetSectorForm

        try:
            with get_db() as db:
                service = AssetSectorService(db)
                asset_sector = service.get(selected_id)

                form = AssetSectorForm(
                    asset_sector_id=selected_id,
                    initial_data={
                        'name': asset_sector.name,
                        'asset_type_id': asset_sector.asset_type_id
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
            title=t('delete_asset_sector'),
            service_cls=AssetSectorService,
            on_deleted=self.load_data,
        )

    def open_details(self, selected_id):
        from holdings_tracker_desktop.ui.dialogs.asset_sector_details_dialog import (
            AssetSectorDetailsDialog
        )

        AssetSectorDetailsDialog(
            asset_sector_id=selected_id,
            parent=self
        ).exec()

    def _populate_table(self, items):
        prepare_table(self.table, 3, len(items))

        self.table.setHorizontalHeaderLabels([t("name"), t("asset_type"), t("assets")])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        for row, item in enumerate(items):
            self.table.setItem(row, 0, table_item(item['name'], item['id']))
            self.table.setItem(row, 1, table_item(item['asset_type_name']))
            self.table.setItem(row, 2, table_item(str(item['assets_count'])))
