from pydantic import ValidationError
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
  QWidget, QDialog, QMessageBox, QVBoxLayout, QFormLayout, QDialogButtonBox, QDoubleSpinBox
)

from holdings_tracker_desktop.ui.core import t
from holdings_tracker_desktop.ui.core.errors import error_text
from holdings_tracker_desktop.ui.core.translations import TRANSLATIONS

# Schema fields whose label key differs from the field name without "_id".
FIELD_LABEL_KEYS = {
    "type_id": "type",
    "event_type": "type",
    "price": "unit_price",
}

# Pydantic error types that just mean "fill this field in".
REQUIRED_ERROR_TYPES = {
    "missing", "int_type", "int_parsing", "decimal_type", "decimal_parsing",
    "date_type", "string_type", "enum",
}

ERROR_TYPE_KEYS = {
    "string_too_short": "validation_too_short",
    "string_too_long": "validation_too_long",
}

class TrimmedDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that hides trailing zeros (100 instead of 100.000000)."""

    def textFromValue(self, value: float) -> str:
        locale = self.locale()
        text = locale.toString(value, "f", self.decimals())
        text = text.replace(locale.groupSeparator(), "")

        decimal_point = locale.decimalPoint()
        if decimal_point in text:
            text = text.rstrip("0").rstrip(decimal_point)

        return text

class BaseFormDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def handle_validation_error(self, error: ValidationError):
        messages = []

        for err in error.errors():
            message = self._translate_validation_message(err)
            label = self._field_label(err["loc"])
            messages.append(f"{label}: {message}" if label else message)

        QMessageBox.warning(
            self,
            t("validation_error"),
            "\n".join(messages)
        )

    def handle_generic_error(self, error: Exception):
        QMessageBox.critical(
            self,
            t("error"),
            error_text(error)
        )

    def _field_label(self, loc: tuple) -> str:
        if not loc:
            return ""

        field = str(loc[-1])
        return t(FIELD_LABEL_KEYS.get(field, field.removesuffix("_id")))

    def _is_empty_string_error(self, err: dict) -> bool:
        return err["type"] == "string_too_short" and not str(err.get("input") or "").strip()

    def _translate_validation_message(self, err: dict) -> str:
        error_type = err["type"]

        if error_type in REQUIRED_ERROR_TYPES or self._is_empty_string_error(err):
            key = "validation_required"
        else:
            key = ERROR_TYPE_KEYS.get(error_type, f"validation_{error_type}")

        if key in TRANSLATIONS["en_US"]:
            ctx = dict(err.get("ctx", {}))

            if "fields" in ctx:
                ctx["fields"] = ", ".join(
                    self._field_label((field.strip(),)) for field in ctx["fields"].split(",")
                )

            return t(key).format(**ctx)

        return err["msg"].removeprefix("Value error, ")

    def create_decimal_spinbox(
            self, 
            decimals: int = 2, 
            minimum: float = 0.0, 
            maximum: float = 10**12,
            step: float = 0.01,
            default: float = 0.0,
            trim_zeros: bool = False
        ) -> QDoubleSpinBox:
        spin = TrimmedDoubleSpinBox() if trim_zeros else QDoubleSpinBox()
        spin.setDecimals(decimals)
        spin.setMinimum(minimum)
        spin.setMaximum(maximum)
        spin.setSingleStep(step)
        spin.setValue(default)
        spin.setAlignment(Qt.AlignRight)
        spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        return spin

    def _setup_ui(self):
        self.setMinimumWidth(350)
        self._main_layout = QVBoxLayout(self)
        self._form_layout = QFormLayout()
        self._form_layout.setLabelAlignment(Qt.AlignRight)
        self._main_layout.addLayout(self._form_layout)

        self._build_form(self._form_layout)
        self._build_buttons()

    def _build_form(self, form_layout: QFormLayout):
        pass

    def _save(self):
        pass

    def _build_buttons(self):
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText(t("save"))
        buttons.button(QDialogButtonBox.Cancel).setText(t("cancel"))
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        self._main_layout.addWidget(buttons)

    def _on_accept(self):
        try:
            self._save()
            self.accept()

        except ValidationError as e:
            self.handle_validation_error(e)

        except Exception as e:
            self.handle_generic_error(e)
