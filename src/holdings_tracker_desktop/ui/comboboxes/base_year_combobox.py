from PySide6.QtCore import Qt

from holdings_tracker_desktop.ui.comboboxes.base_combobox import BaseComboBox
from holdings_tracker_desktop.ui.core import t

class BaseYearComboBox(BaseComboBox):
    def __init__(self, parent=None):
        super().__init__("select_year", parent, searchable=True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setObjectName("YearComboBox")
        self._connect_reload_signals()
        self.reload()

    def _connect_reload_signals(self):
        pass

    def _load_years(self) -> list[int]:
        pass

    def reload(self):
        selected_year = self.currentData()

        self.blockSignals(True)
        self.clear()

        self._setup_placeholder()

        for year in self._load_years():
            self.addItem(str(year), year)

        # Keep the year the user was looking at; fall back to the most recent one.
        selected_index = self.findData(selected_year) if selected_year is not None else -1

        if selected_index > 0:
            self.setCurrentIndex(selected_index)
        elif self.count() > 1:
            self.setCurrentIndex(1)

        self.blockSignals(False)
        self.currentIndexChanged.emit(self.currentIndex())
