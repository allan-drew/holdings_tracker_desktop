from decimal import Decimal

from PySide6.QtCore import QDate

from holdings_tracker_desktop.database import get_db
from holdings_tracker_desktop.models.asset_event import AssetEventType
from holdings_tracker_desktop.schemas.asset_event import AssetEventCreate, AssetEventUpdate
from holdings_tracker_desktop.services.asset_event_service import AssetEventService
from holdings_tracker_desktop.ui.comboboxes import AssetComboBox, EventTypeComboBox
from holdings_tracker_desktop.ui.core import t
from holdings_tracker_desktop.ui.forms.base_form_dialog import BaseFormDialog
from holdings_tracker_desktop.ui.forms.date_input import DateInput

class AssetEventForm(BaseFormDialog):
    def __init__(self, asset_event_id=None, asset_id=None, initial_data=None, parent=None):
        super().__init__(parent)
        self._init_state(asset_event_id, asset_id, initial_data)
        self._load_initial_data()
        self.setWindowTitle(
            t("edit_asset_event") if self.is_edit_mode else t("new_asset_event")
        )

    def _init_state(self, asset_event_id, asset_id, initial_data):
        self.asset_event_id = asset_event_id
        self.asset_id = asset_id
        self.initial_data = initial_data or {}
        self.is_edit_mode = asset_event_id is not None

    def _load_initial_data(self):
        self._load_asset(self.asset_id)

        if not self.initial_data:
            return

        data = self.initial_data

        self._load_date(data)
        self._load_event_type(data)
        self._load_target_asset(data)
        self._load_financial_fields(data)

    def _load_asset(self, asset_id):
        if asset_id is None:
            return

        index = self.asset_combo.findData(asset_id)
        if index >= 0:
            self.asset_combo.setCurrentIndex(index)
            self.asset_combo.setEnabled(False)

    def _load_date(self, data: dict):
        if data.get("date"):
            qdate = QDate(data["date"])
            self.date_input.setDate(qdate)

    def _load_event_type(self, data: dict):
        event_type = data.get("event_type")
        if not event_type:
            return

        index = self.event_type_combo.findData(event_type)
        if index >= 0:
            self.event_type_combo.setCurrentIndex(index)
            self.event_type_combo.setEnabled(False)

    def _load_target_asset(self, data: dict):
        target_asset = data.get("target_asset_id")
        if not target_asset:
            return

        index = self.target_asset_combo.findData(target_asset)
        if index >= 0:
            self.target_asset_combo.setCurrentIndex(index)
            self.target_asset_combo.setEnabled(False)

    def _load_financial_fields(self, data: dict):
        if data.get("factor") is not None:
            self.factor_input.setValue(float(data["factor"]))

        if data.get("quantity") is not None:
            self.quantity_input.setValue(float(data["quantity"]))

        if data.get("price") is not None:
            self.price_input.setValue(float(data["price"]))

        if data.get("target_quantity") is not None:
            self.target_quantity_input.setValue(float(data["target_quantity"]))

        if data.get("target_unit_price") is not None:
            self.target_unit_price_input.setValue(float(data["target_unit_price"]))

        if data.get("residual_value") is not None:
            self.residual_value_input.setValue(float(data["residual_value"]))

    def _build_form(self, form_layout):
        self._setup_date_input(form_layout)
        self._setup_asset_combo(form_layout)
        self._setup_event_type_combo(form_layout)
        self._setup_target_asset_combo(form_layout)
        self._setup_financial_fields(form_layout)

    def _setup_date_input(self, form_layout):
        self.date_input = DateInput()
        form_layout.addRow(f"{t('date')}:", self.date_input)

    def _setup_asset_combo(self, form_layout):
        self.asset_combo = AssetComboBox()
        form_layout.addRow(f"{t('asset')}:", self.asset_combo)

    def _setup_event_type_combo(self, form_layout):
        self.event_type_combo = EventTypeComboBox()
        self.event_type_combo.currentIndexChanged.connect(
            self._on_event_type_changed
        )
        form_layout.addRow(f"{t('type')}:", self.event_type_combo)

    def _setup_target_asset_combo(self, form_layout):
        self.target_asset_combo = AssetComboBox()
        form_layout.addRow(f"{t('target_asset')}:", self.target_asset_combo)

    def _setup_financial_fields(self, form_layout):
        self.factor_input = self.create_decimal_spinbox(decimals=6, step=0.000001)
        self.quantity_input = self.create_decimal_spinbox(decimals=0, step=1)
        self.price_input = self.create_decimal_spinbox()
        self.target_quantity_input = self.create_decimal_spinbox(decimals=0, step=1)
        self.target_unit_price_input = self.create_decimal_spinbox()
        self.residual_value_input = self.create_decimal_spinbox()

        form_layout.addRow(f"{t('factor')}:", self.factor_input)
        form_layout.addRow(f"{t('quantity')}:", self.quantity_input)
        form_layout.addRow(f"{t('unit_price')}:", self.price_input)
        form_layout.addRow(f"{t('target_quantity')}:", self.target_quantity_input)
        form_layout.addRow(f"{t('target_unit_price')}:", self.target_unit_price_input)
        form_layout.addRow(f"{t('residual_value')}:", self.residual_value_input)

        self._reset_event_type_fields()

    def _on_event_type_changed(self):
        event_type = self.event_type_combo.currentData()
        self._apply_event_type_ui(event_type)

    def _reset_event_type_fields(self):
        numeric_fields = (
            self.factor_input,
            self.quantity_input,
            self.price_input,
            self.target_quantity_input,
            self.target_unit_price_input,
            self.residual_value_input,
        )

        for field in numeric_fields:
            self._form_layout.setRowVisible(field, False)
            field.setEnabled(False)
            field.setValue(0)

        self._form_layout.setRowVisible(self.target_asset_combo, False)
        self.target_asset_combo.setEnabled(False)
        self.target_asset_combo.setCurrentIndex(-1)

    def _apply_event_type_ui(self, event_type):
        self._reset_event_type_fields()

        match event_type:
            case AssetEventType.SPLIT | AssetEventType.REVERSE_SPLIT:
                self._form_layout.setRowVisible(self.factor_input, True)
                self.factor_input.setEnabled(True)
                self.factor_input.setToolTip(
                    t(f"factor_hint_{event_type.value.lower()}")
                )

            case AssetEventType.AMORTIZATION | AssetEventType.SUBSCRIPTION:
                self._form_layout.setRowVisible(self.quantity_input, True)
                self._form_layout.setRowVisible(self.price_input, True)
                self.quantity_input.setEnabled(True)
                self.price_input.setEnabled(True)

            case AssetEventType.TOTAL_CONVERSION:
                self._form_layout.setRowVisible(self.target_asset_combo, True)
                self._form_layout.setRowVisible(self.target_quantity_input, True)
                self._form_layout.setRowVisible(self.target_unit_price_input, True)
                self._form_layout.setRowVisible(self.residual_value_input, True)
                self.target_asset_combo.setEnabled(True)
                self.target_quantity_input.setEnabled(True)
                self.target_unit_price_input.setEnabled(True)
                self.residual_value_input.setEnabled(True)

        self.adjustSize()

    def _save(self):
        asset_id = self.asset_id
        event_type =  self.event_type_combo.currentData()
        date = self.date_input.date().toPython()

        factor = quantity = price = None
        target_asset_id = target_quantity = target_unit_price = residual_value = None

        match event_type:
            case AssetEventType.SPLIT | AssetEventType.REVERSE_SPLIT:
                factor = self._decimal(self.factor_input)

            case AssetEventType.AMORTIZATION | AssetEventType.SUBSCRIPTION:
                quantity = self._decimal(self.quantity_input)
                price = self._decimal(self.price_input)

            case AssetEventType.TOTAL_CONVERSION:
                target_asset_id = self.target_asset_combo.currentData()
                target_quantity = self._decimal(self.target_quantity_input)
                target_unit_price = self._decimal(self.target_unit_price_input)
                residual_value = self._decimal(self.residual_value_input)

        with get_db() as db:
            service = AssetEventService(db)

            if self.is_edit_mode:
                update_data = AssetEventUpdate(
                    asset_id=asset_id,
                    event_type=event_type,
                    date=date, 
                    factor=factor,
                    quantity=quantity,
                    price=price,
                    target_asset_id=target_asset_id,
                    target_quantity=target_quantity,
                    target_unit_price=target_unit_price,
                    residual_value=residual_value,
                )
                service.update(self.asset_event_id, update_data)
            else:
                create_data = AssetEventCreate(
                    asset_id=asset_id,
                    event_type=event_type,
                    date=date,
                    factor=factor,
                    quantity=quantity,
                    price=price,
                    target_asset_id=target_asset_id,
                    target_quantity=target_quantity,
                    target_unit_price=target_unit_price,
                    residual_value=residual_value,
                )
                service.create(create_data)

    def _decimal(self, spinbox):
        return Decimal(str(spinbox.value())) 
