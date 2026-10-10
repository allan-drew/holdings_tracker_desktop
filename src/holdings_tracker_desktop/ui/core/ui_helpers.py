from decimal import Decimal
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from holdings_tracker_desktop.ui.core.formatters import format_decimal, format_quantity

ALIGN_TEXT = Qt.AlignLeft | Qt.AlignVCenter
ALIGN_NUMBER = Qt.AlignRight | Qt.AlignVCenter
ALIGN_CENTER = Qt.AlignCenter

def prepare_table(table: QTableWidget, columns: int, rows: int) -> None:
    table.clear()
    table.setColumnCount(columns)
    table.setRowCount(rows)

def table_item(text: str, user_role: Optional[Any] = None, align: Qt.AlignmentFlag = ALIGN_CENTER) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(align)

    if user_role is not None:
        item.setData(Qt.UserRole, user_role)

    return item

def decimal_table_item(value: Optional[Decimal], decimals: int = 2, currency: str = "") -> QTableWidgetItem:
    if value is None:
        return table_item("", align=ALIGN_NUMBER)

    text = format_decimal(value, decimals)
    text = f"{currency} {text}".strip()
    return table_item(text, align=ALIGN_NUMBER)

def quantity_table_item(value: Optional[Decimal]) -> QTableWidgetItem:
    if value is None:
        return table_item("", align=ALIGN_NUMBER)

    return table_item(format_quantity(value), align=ALIGN_NUMBER)
