DARK_THEME = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #4b5563;
    border-radius: 4px;
    padding: 5px;
}

QPushButton {
    background-color: #374151;
    color: #ffffff;
    border: none;
    border-radius: 5px;
    padding: 7px 12px;
}

QPushButton:hover {
    background-color: #4b5563;
}

QTableView, QTableWidget {
    background-color: #2d2d2d;
    color: #ffffff;
    gridline-color: #4b5563;
}

QHeaderView::section {
    background-color: #374151;
    color: #ffffff;
    padding: 6px;
    border: none;
}

QMenuBar, QMenu {
    background-color: #1e1e1e;
    color: #ffffff;
}

QMenu::item:selected, QMenuBar::item:selected {
    background-color: #374151;
}
"""


LIGHT_THEME = """
QMainWindow, QWidget {
    background-color: #ffffff;
    color: #1f2937;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #9ca3af;
    border-radius: 4px;
    padding: 5px;
}

QPushButton {
    background-color: #e5e7eb;
    color: #1f2937;
    border: none;
    border-radius: 5px;
    padding: 7px 12px;
}

QPushButton:hover {
    background-color: #d1d5db;
}
"""