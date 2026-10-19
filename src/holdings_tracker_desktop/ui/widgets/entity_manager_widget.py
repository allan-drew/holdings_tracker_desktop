import qtawesome as qta

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QFrame, QHeaderView, QMessageBox, QDialog
)

from holdings_tracker_desktop.database import get_db
from holdings_tracker_desktop.ui.core import t
from holdings_tracker_desktop.ui.core.errors import error_text
from holdings_tracker_desktop.ui.dialogs.confirm_dialog import ConfirmDialog
from holdings_tracker_desktop.ui.widgets.title_widget import TitleWidget
from holdings_tracker_desktop.ui.widgets.translatable_widget import TranslatableWidget
from holdings_tracker_desktop.ui.core.ui_helpers import table_item, decimal_table_item

DEFAULT_ACTIONS = ("add", "edit", "delete")

BUTTONS_CONFIG = {
    "add": "fa5s.plus",
    "edit": "fa5s.edit",
    "delete": "fa5s.trash"
}

class EntityManagerWidget(TranslatableWidget):
    # Table columns joined to name the selected record in confirmations
    RECORD_LABEL_COLUMNS: tuple[int, ...] = (0,)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.buttons = {}
        self._setup_ui()

        if self.supports_details():
            self.table.cellDoubleClicked.connect(self.on_double_clicked)

    def translate_ui(self):
        for action in self.get_enabled_actions():
            self.buttons[action].setText(t(action))

        for name, _, _ in self.get_extra_buttons():
            self.buttons[name].setText(t(name))

        if self.supports_details():
            self.table.setToolTip(t("double_click_to_view_details"))
        else:
            self.table.setToolTip("")

    def load_data(self):
        pass

    def on_show(self):
        """
        Called whenever the widget is displayed by OperationsWidget.
        """
        self.load_data()

    def open_new_form(self):
        pass
    
    def open_edit_form(self):
        pass

    def delete_record(self):
        pass

    def open_details(self):
        pass

    def get_selected_id(self):
        selected_rows = self.table.selectionModel().selectedRows()
        selected_id = self._row_id(selected_rows[0].row()) if selected_rows else None

        if selected_id is None:
            self.show_warning(t("no_row_selected"))

        return selected_id

    def on_add_clicked(self):
        self.open_new_form()

    def on_edit_clicked(self):
        selected_id = self.get_selected_id()
        if selected_id:
            self.open_edit_form(selected_id)

    def on_delete_clicked(self):
        selected_id = self.get_selected_id()
        if selected_id:
            self.delete_record(selected_id)

    def on_double_clicked(self, row: int):
        if not self.supports_details():
            return

        selected_id = self._row_id(row)
        if selected_id:
            self.open_details(selected_id)

    def _row_id(self, row: int):
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def show_warning(self, message: str):
        QMessageBox.warning(self, t("warning"), message)

    def show_error(self, message: str):
        QMessageBox.critical(self, t("error"), message)

    def show_load_error(self, error: Exception):
        self.show_error(t("error_loading").format(error=error_text(error)))

    def show_open_form_error(self, error: Exception):
        self.show_error(t("error_opening_form").format(error=error_text(error)))

    def delete_with_confirmation(self, selected_id, *, title: str, service_cls, on_deleted):
        """Ask for confirmation, delete through `service_cls(db).delete`, then call `on_deleted`."""
        label = self._record_label(selected_id)
        message = t("confirm_delete_item").format(item=label) if label else t("confirm_delete")

        confirmed = self.ask_confirmation(
            title=title,
            message=message,
            confirm_text=t("delete"),
            warning=True,
        )
        if not confirmed:
            return

        try:
            with get_db() as db:
                deleted = service_cls(db).delete(selected_id)

        except Exception as e:
            self.show_error(t("error_deleting").format(error=error_text(e)))
            return

        if deleted:
            on_deleted()
        else:
            self.show_error(t("delete_failed"))

    def ask_confirmation(self, title: str, message: str, **options) -> bool:
        dialog = ConfirmDialog(
            title=title,
            message=message,
            parent=self,
            **options
        )
        return dialog.exec() == QDialog.Accepted

    def _record_label(self, record_id) -> str:
        """Text identifying the record in the table, taken from RECORD_LABEL_COLUMNS."""
        row = next(
            (row for row in range(self.table.rowCount()) if self._row_id(row) == record_id),
            None
        )
        if row is None:
            return ""

        items = (self.table.item(row, column) for column in self.RECORD_LABEL_COLUMNS)
        return " — ".join(item.text() for item in items if item and item.text())

    def get_operations_widget(self):
        parent = self.parent()
        while parent is not None:
            if parent.__class__.__name__ == "OperationsWidget":
                return parent
            parent = parent.parent()
        return None

    def navigate_to(self, widget_cls, *args, **kwargs):
        operations = self.get_operations_widget()
        if operations:
            operations.show_widget(widget_cls, *args, **kwargs)

    def get_enabled_actions(self) -> tuple[str, ...]:
        """
        Override in subclasses to enable/disable default CRUD actions.
        """
        return DEFAULT_ACTIONS

    def get_extra_buttons(self):
        return []

    def get_toolbar_filters(self):
        return []

    def supports_details(self) -> bool:
        return False

    def add_grouped_total_rows(
        self,
        items: list[dict],
        *,
        group_by_key,
        value_key: str,
        value_column: int,
        label_column: int = 0,
        label_text: str | None = None,
        decimals: int = 2,
        currency_key: str | None = None,
        value_item_factory=None,
    ) -> None:
        """Aggregate `items` by `group_by_key` and append total rows to ``self.table``.

        - ``group_by_key``: either a string key to lookup in each item or a callable(item)->group.
        - ``value_key``: the dict key whose numeric values will be summed per group.
        - ``value_column``: the table column index where the summed value will be placed.
        - ``label_column``: the table column index to place the "total" label (default 0).
        - ``label_text``: text to use for the total label (defaults to translation of "total").
        - ``decimals``: number of decimals when formatting numbers.
        - ``currency_key``: optional key name for currency; when provided the group value is used as currency.
        - ``value_item_factory``: optional callable(total, decimals, currency) -> QTableWidgetItem.
        """
        if label_text is None:
            label_text = t("total")

        totals_by_group = {}

        for item in items:
            group = group_by_key(item) if callable(group_by_key) else item.get(group_by_key, "")
            total_value = item.get(value_key, 0) or 0

            if group in totals_by_group:
                totals_by_group[group] += total_value
            else:
                totals_by_group[group] = total_value

        for group, total in totals_by_group.items():
            total_row = self.table.rowCount()
            self.table.insertRow(total_row)

            total_item = table_item(label_text)
            total_item.setFont(self.font_demi_bold)
            self.table.setItem(total_row, label_column, total_item)

            currency = group if currency_key else ""

            if value_item_factory:
                value_item = value_item_factory(total, decimals, currency)
            else:
                value_item = decimal_table_item(total, decimals, currency)

            value_item.setFont(self.font_demi_bold)
            self.table.setItem(total_row, value_column, value_item)

            self._make_row_unselectable(total_row)

    def _make_row_unselectable(self, row: int) -> None:
        for column in range(self.table.columnCount()):
            item = self.table.item(row, column)
            if item is None:
                item = table_item("")
                self.table.setItem(row, column, item)
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)

    @property
    def font_demi_bold(self):
        """Return a cached QFont with DemiBold weight.

        The font is created on first access and stored on the instance so
        subclasses can reuse the same QFont even if accessed before
        `super().__init__()` completes.
        """
        if not hasattr(self, "_font_demi_bold") or self._font_demi_bold is None:
            self._font_demi_bold = QFont()
            self._font_demi_bold.setWeight(QFont.DemiBold)
        return self._font_demi_bold

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 0)
        main_layout.setSpacing(5)

        self.title_widget = TitleWidget()
        main_layout.addWidget(self.title_widget)

        self._setup_body_frame(main_layout)

    def _setup_body_frame(self, main_layout):
        body_frame = QFrame()
        body_frame.setObjectName("BodyFrame")
        body_layout = QVBoxLayout(body_frame)

        self._setup_toolbar(body_layout)
        self._setup_table(body_layout)

        main_layout.addWidget(body_frame)

    def _setup_toolbar(self, body_layout):
        toolbar = QHBoxLayout()

        for widget in self.get_toolbar_filters():
            toolbar.addWidget(widget)

        for action in self.get_enabled_actions():
            icon = BUTTONS_CONFIG[action]

            button = QPushButton("")
            button.setIcon(qta.icon(icon, color="#808080"))
            self.buttons[action] = button
            toolbar.addWidget(button)

            handler = getattr(self, f"on_{action}_clicked", None)
            if handler:
                button.clicked.connect(handler)

        for name, icon, handler in self.get_extra_buttons():
            button = QPushButton("")
            button.setIcon(qta.icon(icon, color="#808080"))
            self.buttons[name] = button
            toolbar.addWidget(button)
            button.clicked.connect(handler)

        body_layout.addLayout(toolbar)

    def _setup_table(self, body_layout):
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        body_layout.addWidget(self.table)
