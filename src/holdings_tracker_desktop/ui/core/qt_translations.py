from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTranslator

from holdings_tracker_desktop.ui.core import translations as i18n

_translator: QTranslator | None = None
_installed_lang: str | None = None

def apply_language(lang: str) -> None:
    """Switch the app texts and Qt's own texts to `lang`."""
    i18n.current_lang = lang
    install_qt_translator(lang)

def install_qt_translator(lang: str) -> None:
    """Load Qt's own texts (context menus, standard dialogs) in `lang`, replacing the previous ones."""
    global _translator, _installed_lang

    app = QCoreApplication.instance()
    if app is None or lang == _installed_lang:
        return

    _installed_lang = lang

    if _translator is not None:
        app.removeTranslator(_translator)
        _translator.deleteLater()
        _translator = None

    # Qt's source texts are already English
    if lang.startswith("en"):
        return

    translator = QTranslator(app)
    directory = QLibraryInfo.path(QLibraryInfo.TranslationsPath)

    if translator.load(f"qtbase_{lang}", directory):
        app.installTranslator(translator)
        _translator = translator
    else:
        translator.deleteLater()
