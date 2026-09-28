import sys
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QApplication
from PySide6.QtCore import Qt

from holdings_tracker_desktop.ui.core.themes import DARK_THEME, LIGHT_THEME
from holdings_tracker_desktop.version import get_app_version
from holdings_tracker_desktop.ui.core import translations as i18n
from holdings_tracker_desktop.ui.core.app_settings import AppSettings
from holdings_tracker_desktop.ui.styles import base
from holdings_tracker_desktop.ui.widgets.charts_widget import ChartsWidget
from holdings_tracker_desktop.ui.widgets.operations_widget import OperationsWidget

WINDOW_MARGIN = 5
WINDOW_SPACING = 5

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._init_state()
        self._init_ui()

    def set_language(self, lang):
        """Change language globally and update UI text without rebuilding the window."""
        if i18n.current_lang == lang:
            return

        i18n.current_lang = lang
        self.settings.set_language(lang)
        self.translate_ui()

    def translate_ui(self):
        for widget in self.widgets_with_translation:
            widget.translate_ui()

    def register_translatable(self, widget):
        if widget not in self.widgets_with_translation:
            self.widgets_with_translation.append(widget)

    def _init_state(self):
        self.widgets_with_translation = []
        self.settings = AppSettings()
        i18n.current_lang = self.settings.get_language()

    def _init_ui(self):
        self.setWindowTitle(f"Holdings Tracker v{get_app_version()}")
        self._setup_layout()
        self._setup_panels()

    def _apply_system_theme(self):
        app = QApplication(sys.argv)
        is_dark = (
            app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        )
        self.setStyleSheet(DARK_THEME if is_dark else LIGHT_THEME)

    def _setup_layout(self):
        self.central_widget = QWidget()
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(
            WINDOW_MARGIN, WINDOW_MARGIN, 
            WINDOW_MARGIN, WINDOW_MARGIN
        )
        self.main_layout.setSpacing(WINDOW_SPACING)
        self.setCentralWidget(self.central_widget)

    def _setup_panels(self):
        panels = [
            ("LeftPanel", OperationsWidget(self)),
            ("RightPanel", ChartsWidget(self)),
        ]

        for name, panel in panels:
            panel.setObjectName(name)
            self.main_layout.addWidget(panel, stretch=1)
