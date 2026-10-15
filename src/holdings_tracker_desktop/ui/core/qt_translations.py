from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTranslator

_translator: QTranslator | None = None

def install_qt_translator(lang: str) -> None:
    """Load Qt's own texts (context menus, standard dialogs) in `lang`, replacing the previous ones."""
    global _translator

    app = QCoreApplication.instance()
    if app is None:
        return

    if _translator is not None:
        app.removeTranslator(_translator)
        _translator = None

    translator = QTranslator(app)
    directory = QLibraryInfo.path(QLibraryInfo.TranslationsPath)

    # "qtbase_en_US" falls back to "qtbase_en"
    if translator.load(f"qtbase_{lang}", directory):
        app.installTranslator(translator)
        _translator = translator
