from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox, QStyle

from holdings_tracker_desktop.ui.core import t

ICON_SIZE = 32

class ConfirmDialog(QDialog):
    def __init__(
        self,
        title: str,
        message: str,
        parent=None,
        confirm_text: str | None = None,
        warning: bool = False
    ):
        super().__init__(parent)
        self.title = title
        self.message = message
        self.confirm_text = confirm_text or t("yes")
        self.cancel_text = t("cancel") if confirm_text else t("no")
        self.warning = warning
        self._setup_ui()

    def _setup_ui(self):
        self.setMinimumWidth(350)
        self.setWindowTitle(self.title)

        layout = QVBoxLayout(self)

        message_layout = QHBoxLayout()
        message_layout.setSpacing(12)

        if self.warning:
            icon = self.style().standardIcon(QStyle.SP_MessageBoxWarning)
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(ICON_SIZE, ICON_SIZE))
            message_layout.addWidget(icon_label)

        label = QLabel(self.message)
        label.setWordWrap(True)
        message_layout.addWidget(label, stretch=1)

        layout.addLayout(message_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        buttons.button(QDialogButtonBox.Ok).setText(self.confirm_text)
        buttons.button(QDialogButtonBox.Cancel).setText(self.cancel_text)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

        buttons.button(QDialogButtonBox.Cancel).setDefault(True)
        buttons.button(QDialogButtonBox.Cancel).setFocus()
