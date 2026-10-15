import sys
import traceback

def main():
    """
    Application entry point.
    Shows splash screen during Bootstrap initialization, then launches main window.
    Uses lazy loading to minimize startup time before splash screen appears.
    """
    # Minimal imports - only what's needed before splash
    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication(sys.argv)

    # Translate Qt's own texts before any dialog (including startup errors) appears
    from holdings_tracker_desktop.ui.core.app_settings import AppSettings
    from holdings_tracker_desktop.ui.core.qt_translations import apply_language
    apply_language(AppSettings().get_language())

    # Show splash screen while Bootstrap runs
    from holdings_tracker_desktop.ui.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()  # Force immediate display

    try:
        # Lazy load Bootstrap - happens while splash is visible
        from holdings_tracker_desktop.database.bootstrap import Bootstrap, BootstrapError
        Bootstrap().run()
    except Exception as e:
        splash.close()
        
        # Lazy load for error handling
        from holdings_tracker_desktop.database.bootstrap import BootstrapError
        if isinstance(e, BootstrapError):
            detailed_error = traceback.format_exc()
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Initialization Error")
            msg.setText("The application failed to initialize properly.")
            msg.setInformativeText("Click 'Show Details' to see the technical error.")
            msg.setDetailedText(detailed_error)
            msg.exec()

        sys.exit(1)

    # Lazy load UI components after bootstrap succeeds
    from PySide6.QtGui import QFont
    import qtawesome as qta
    from holdings_tracker_desktop.ui.main_window import MainWindow

    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setWindowIcon(qta.icon("fa5s.chart-bar"))

    window = MainWindow()
    splash.close()  # Hide splash screen before showing main window

    window.showMaximized()
    window.raise_()
    window.activateWindow()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
