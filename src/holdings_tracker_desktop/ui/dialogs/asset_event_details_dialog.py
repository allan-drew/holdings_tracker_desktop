from holdings_tracker_desktop.ui.core import t
from holdings_tracker_desktop.ui.core.formatters import format_date, format_datetime, format_decimal, format_quantity
from holdings_tracker_desktop.ui.dialogs.base_details_dialog import BaseDetailsDialog

class AssetEventDetailsDialog(BaseDetailsDialog):
    def __init__(self, asset_event_id: int, parent=None):
        self.asset_event_id = asset_event_id
        super().__init__(parent)

        self._load_data()
        self.setWindowTitle(t("asset_event_details"))

    def _load_data(self):
        from holdings_tracker_desktop.database import get_db
        from holdings_tracker_desktop.services.asset_event_service import AssetEventService

        with get_db() as db:
            service = AssetEventService(db)
            event = service.get_details(self.asset_event_id)

            self.add_detail(t("asset"), event.asset.ticker)
            self.add_detail(t("date"), format_date(event.date))
            self.add_detail(t("type"), t(event.event_type.value.lower()))

            if event.factor:
                self.add_detail(t("factor"), format_quantity(event.factor))

            if event.quantity:
                self.add_detail(t("quantity"), format_quantity(event.quantity))

            if event.price:
                self.add_detail(t("unit_price"), format_decimal(event.price))

            if event.target_asset:
                self.add_detail(t("target_asset"), event.target_asset.ticker)

            if event.target_quantity:
                self.add_detail(t("target_quantity"), format_quantity(event.target_quantity))

            if event.target_unit_price:
                self.add_detail(t("target_unit_price"), format_decimal(event.target_unit_price))

            if event.residual_value is not None:
                self.add_detail(t("residual_value"), format_decimal(event.residual_value))

            self.add_detail(t("created_at"), format_datetime(event.created_at_local))
            self.add_detail(t("updated_at"), format_datetime(event.updated_at_local))
