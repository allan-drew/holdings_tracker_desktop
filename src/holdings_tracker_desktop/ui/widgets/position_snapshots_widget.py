from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView

from holdings_tracker_desktop.database import get_db
from holdings_tracker_desktop.services.position_snapshot_service import PositionSnapshotService
from holdings_tracker_desktop.ui.comboboxes import PositionSnapshotYearComboBox, AssetTypeComboBox
from holdings_tracker_desktop.ui.core import t
from holdings_tracker_desktop.ui.core.formatters import format_date
from holdings_tracker_desktop.ui.core.ui_helpers import prepare_table, table_item, decimal_table_item, quantity_table_item
from holdings_tracker_desktop.ui.widgets.entity_manager_widget import EntityManagerWidget

class PositionSnapshotsWidget(EntityManagerWidget):
    def __init__(self, asset_id: int | None = None, origin: str | None = None, parent=None):
        self.asset_id = asset_id
        self.origin = origin
        self.year = None

        self._setup_filters()

        super().__init__(parent)

        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)

    def get_toolbar_filters(self):
        filters = []
        if self.year_filter:
            filters.append(self.year_filter)
        if self.asset_type_filter:
            filters.append(self.asset_type_filter)
        return filters

    def load_data(self):
        self.ui_data = []

        try:
            with get_db() as db:
                service = PositionSnapshotService(db)

                if self.asset_id:
                    self.ui_data = service.list_all_for_ui_by_asset(self.asset_id)
                else:
                    self.year = self.year_filter.currentData()
                    if self.year is not None:
                        asset_type_id = self.asset_type_filter.currentData() if self.asset_type_filter else None
                        self.ui_data = service.list_all_for_ui_by_year(self.year, asset_type_id=asset_type_id)

        except Exception as e:
            self.show_error(f"Error loading position snapshots: {str(e)}")
            self.table.setRowCount(0)

        self.translate_ui()

    def translate_ui(self):
        super().translate_ui()

        if self.year:
            self.title_widget.set_primary_text(f"{t('position')} — {self.year}")
            self.title_widget.set_secondary_text(str(len(self.ui_data)))
        else:
            self.title_widget.set_primary_text(t("position"))

        if self.year_filter:
            self.year_filter.translate_placeholder()

        if self.asset_type_filter:
            self.asset_type_filter.translate_placeholder()

        if self.asset_id is None:
            self.table.setToolTip(t("double_click_to_view_details"))
        else:
            self.table.setToolTip("")

        self._populate_table(self.ui_data)

    def get_enabled_actions(self):
        return ()

    def get_extra_buttons(self):
        return [("back", "fa5s.arrow-left", self.on_back_clicked)] if self.asset_id else []

    def on_item_double_clicked(self, item):
        if self.asset_id is not None:
            return

        row = item.row()
        asset_item = self.table.item(row, 0)
        asset_id = asset_item.data(Qt.UserRole)

        if asset_id:
            self.navigate_to(PositionSnapshotsWidget, asset_id=asset_id, origin="global")

    def on_back_clicked(self):
        if self.origin == "global":
            self.navigate_to(PositionSnapshotsWidget)
        else:
            from holdings_tracker_desktop.ui.widgets.assets_widget import AssetsWidget
            self.navigate_to(AssetsWidget)

    def _setup_filters(self):
        if self.asset_id is None:
            self.year_filter = PositionSnapshotYearComboBox()
            self.year_filter.currentIndexChanged.connect(self.load_data)

            self.asset_type_filter = AssetTypeComboBox(placeholder_key="all")
            self.asset_type_filter.setObjectName("FilterComboBox")
            self.asset_type_filter.currentIndexChanged.connect(self.load_data)
        else:
            self.year_filter = None
            self.asset_type_filter = None

    def _populate_table(self, items):
        if self.asset_id is not None:
            self._populate_table_single_asset(items)
        else:
            self._populate_table_all_assets(items)

    def _populate_table_single_asset(self, items):
        prepare_table(self.table, 6, len(items))
        self.table.setHorizontalHeaderLabels(
            [t("asset"), t("date"), t("quantity_abbr"), t("avg_price"), t("total_cost"), t("origin")]
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        for row, item in enumerate(items):
            self.table.setItem(row, 0, table_item(item['asset_ticker'], item['id']))
            self.table.setItem(row, 1, table_item(format_date(item['snapshot_date'])))
            self.table.setItem(row, 2, quantity_table_item(item['quantity']))
            currency = item.get("asset_currency", "")
            self.table.setItem(row, 3, decimal_table_item(item['avg_price'], 2, currency))
            self.table.setItem(row, 4, decimal_table_item(item['total_cost'], 2, currency))
            self.table.setItem(row, 5, table_item(t(item['origin_action'])))

    def _populate_table_all_assets(self, items):
        prepare_table(self.table, 4, len(items))
        self.table.setHorizontalHeaderLabels(
            [t("asset"), t("quantity_abbr"), t("avg_price"), t("total_cost")]
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        for row, item in enumerate(items):
            self.table.setItem(row, 0, table_item(item['asset_ticker'], item['asset_id']))
            self.table.setItem(row, 1, quantity_table_item(item['quantity']))
            currency = item.get("asset_currency", "")
            self.table.setItem(row, 2, decimal_table_item(item['avg_price'], 2, currency))
            self.table.setItem(row, 3, decimal_table_item(item['total_cost'], 2, currency))

        if self.year and items:
            self.add_grouped_total_rows(
                items,
                group_by_key="asset_currency",
                value_key="total_cost",
                value_column=3,
                label_column=0,
                label_text=t("total"),
                decimals=2,
                currency_key="asset_currency",
            )
