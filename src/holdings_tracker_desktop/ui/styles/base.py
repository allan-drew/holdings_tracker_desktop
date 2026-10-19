BUTTONS = """
QPushButton {
    background-color: #f5f5f5;
    border: 1px solid #c6c6c6;
    padding: 4px 8px;
    border-radius: 6px;
    min-width: 64px;
    min-height: 20px;
    outline: none;
}

QPushButton:hover {
    background-color: #eaeaea;
}

QPushButton:pressed {
    background-color: #dcdcdc;
}

QPushButton:disabled {
    background-color: #eeeeee;
    color: #999999;
}
"""

COMBOBOXES = """
QComboBox#YearComboBox,
QComboBox#FilterComboBox {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #c6c6c6;
    padding: 4px 8px;
}
"""

FRAMES = """
QFrame#TitleFrame,
QFrame#BodyFrame {
    border: 1px solid #cccccc;
    border-radius: 8px;
    background: #f8f8f8;
}
"""

LABELS = """
QLabel#TitleLabel {
    font-size: 13pt;
    font-weight: bold;
}
QLabel#SecondaryTitleLabel {
    font-size: 9pt;
    font-weight: bold;
}
"""

TABLES = """
QTableWidget {
    background: #ffffff;
    border: 1px solid #dcdcdc;
    border-radius: 6px;
    gridline-color: #e0e0e0;
    selection-background-color: #0066cc;
    selection-color: white;
    outline: none;
}

QTableWidget::item {
    border: none;
}
"""

HEADERS = """
QHeaderView {
    background-color: #f2f2f2;
}

QHeaderView::section {
    background-color: #f2f2f2;
    color: #333;
    padding: 4px 8px;
    border: none;
    border-bottom: 1px solid #d0d0d0;
    font-weight: 600;
    font-size: 10.5pt;
}

QHeaderView::section:hover {
    background-color: #eaeaea;
}

QHeaderView::section:pressed {
    background-color: #dddddd;
}
"""

SCROLLS = """
QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: white;
    border-radius: 8px;
}
"""


DARK_BUTTONS = """
QPushButton {
    background-color: #383838;
    border: 1px solid #555555;
    color: #eeeeee;
    padding: 4px 8px;
    border-radius: 6px;
    min-width: 64px;
    min-height: 20px;
    outline: none;
}

QPushButton:hover {
    background-color: #454545;
}

QPushButton:pressed {
    background-color: #505050;
}

QPushButton:disabled {
    background-color: #303030;
    color: #888888;
}
"""

DARK_COMBOBOXES = """
QComboBox#YearComboBox,
QComboBox#FilterComboBox {
    background-color: #383838;
    color: #eeeeee;
    border: 1px solid #555555;
    padding: 4px 8px;
}
"""

DARK_FRAMES = """
QFrame#TitleFrame,
QFrame#BodyFrame {
    border: 1px solid #555555;
    border-radius: 8px;
    background: #2b2b2b;
}
"""

DARK_TABLES = """
QTableWidget {
    background: #242424;
    color: #eeeeee;
    border: 1px solid #555555;
    border-radius: 6px;
    gridline-color: #404040;
    selection-background-color: #3478c7;
    selection-color: white;
    outline: none;
}

QTableWidget::item {
    border: none;
}
"""

DARK_HEADERS = """
QHeaderView {
    background-color: #333333;
}

QHeaderView::section {
    background-color: #333333;
    color: #eeeeee;
    padding: 4px 8px;
    border: none;
    border-bottom: 1px solid #555555;
    font-weight: 600;
    font-size: 10.5pt;
}

QHeaderView::section:hover {
    background-color: #454545;
}

QHeaderView::section:pressed {
    background-color: #505050;
}
"""

DARK_SCROLLS = """
QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: #242424;
    border-radius: 8px;
}
"""


def base_styles(dark: bool = False):
    if dark:
        return (
            DARK_BUTTONS +
            DARK_COMBOBOXES +
            DARK_FRAMES +
            LABELS +
            DARK_TABLES +
            DARK_HEADERS +
            DARK_SCROLLS
        )

    return (
        BUTTONS +
        COMBOBOXES +
        FRAMES +
        LABELS +
        TABLES +
        HEADERS +
        SCROLLS
    )
