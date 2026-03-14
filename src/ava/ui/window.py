from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from ava.app.bootstrap import BootstrapContext
from ava.ui.app_state import QtAssistantState
from ava.ui.bridge import UiBridge


def run_ui(context: BootstrapContext) -> int:
    app = QGuiApplication.instance() or QGuiApplication([])
    app.setApplicationName(context.settings.app_name)
    icon_path = Path(__file__).with_name("qml") / "ava.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    engine = QQmlApplicationEngine()
    app_state = QtAssistantState(context.state)
    bridge = UiBridge(context.controller, app_state)

    engine.rootContext().setContextProperty("appState", app_state)
    engine.rootContext().setContextProperty("uiBridge", bridge)

    qml_path = Path(__file__).with_name("qml") / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    return app.exec()
