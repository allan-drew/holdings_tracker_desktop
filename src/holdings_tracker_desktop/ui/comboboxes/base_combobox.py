from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter

from holdings_tracker_desktop.ui.core import t

class BaseComboBox(QComboBox):
    def __init__(
        self,
        placeholder_key: str, 
        parent=None, 
        *, 
        searchable: bool = False,
        max_visible_items: int = 15
    ):
        super().__init__(parent)

        self.placeholder_key = placeholder_key

        self.setInsertPolicy(QComboBox.NoInsert)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMaxVisibleItems(max_visible_items)
        self.set_searchable(searchable)

        self._setup_placeholder()

    def set_searchable(self, enabled: bool):
        self.setEditable(enabled)

        if not enabled:
            self.setCompleter(None)
            return

        completer = QCompleter(self.model(), self)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(completer)

        self.lineEdit().editingFinished.connect(self._sync_index_with_text)

    def currentData(self, role=Qt.UserRole):
        # Typed text that was never confirmed would otherwise leave the
        # previously selected item as the current data.
        self._sync_index_with_text()
        return super().currentData(role)

    def _sync_index_with_text(self):
        """Select the item matching the typed text (case-insensitive), or the placeholder."""
        if not self.isEditable() or self.count() == 0:
            return

        index = self.findText(self.currentText().strip(), Qt.MatchFixedString)
        if index < 0:
            index = 0

        if index != self.currentIndex():
            self.setCurrentIndex(index)
        elif self.currentText() != self.itemText(index):
            self.setEditText(self.itemText(index))

    def _setup_placeholder(self):
        self.clear()
        self.addItem(t(self.placeholder_key), None)

    def reload(self):
        pass

    def translate_placeholder(self):
        self.setItemText(0, t(self.placeholder_key))
