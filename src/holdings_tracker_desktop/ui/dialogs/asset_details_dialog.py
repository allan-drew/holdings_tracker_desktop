from holdings_tracker_desktop.ui.core import t
from holdings_tracker_desktop.ui.core.formatters import format_datetime
from holdings_tracker_desktop.ui.dialogs.base_details_dialog import BaseDetailsDialog

class AssetDetailsDialog(BaseDetailsDialog):
    def __init__(self, asset_id: int, parent=None):
        self.asset_id = asset_id
        super().__init__(parent)

        self._load_data()
        self.setWindowTitle(t("asset_details"))

    def _load_data(self):
        from holdings_tracker_desktop.database import get_db
        from holdings_tracker_desktop.services.asset_service import AssetService

        with get_db() as db:
            service = AssetService(db)
            asset = service.get_details(self.asset_id)

            self.add_detail(t("ticker"), asset.ticker)
            self.add_detail(t("type"), asset.asset_type.name)
            self.add_detail(t("currency"), asset.currency.code)
            self.add_detail(t("sector"), asset.sector.name if asset.sector else "-")
            self.add_detail(t("broker_notes"), str(asset.broker_notes_count))
            self.add_detail(t("asset_events"), str(asset.events_count))
            self.add_detail(t("asset_ticker_history"), str(asset.ticker_histories_count))
            self.add_detail(t("created_at"), format_datetime(asset.created_at_local))
            self.add_detail(t("updated_at"), format_datetime(asset.updated_at_local))
