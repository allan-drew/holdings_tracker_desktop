from PySide6.QtCore import QObject, Signal

class GlobalSignals(QObject):
    asset_events_updated = Signal()
    asset_types_updated = Signal()
    assets_updated = Signal()
    broker_notes_updated = Signal()

global_signals = GlobalSignals()
