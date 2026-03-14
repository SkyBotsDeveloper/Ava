from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from ava.app.bootstrap import BootstrapContext
from ava.ui.app_state import QtAssistantState
from ava.ui.bridge import UiBridge
from ava.ui.history_model import HistoryListModel


def _create_tray_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QColor("#7dd3fc"))
    painter.setBrush(QColor("#09111f"))
    painter.drawEllipse(6, 6, 52, 52)
    painter.setBrush(QColor("#7dd3fc"))
    painter.setPen(QColor("#7dd3fc"))
    painter.drawEllipse(23, 23, 18, 18)
    painter.end()
    return QIcon(pixmap)


def _create_tray(window, app: QApplication) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(_create_tray_icon(), parent=app)
    tray.setToolTip("Ava")

    menu = QMenu()
    show_action = QAction("Show Ava", parent=menu)
    hide_action = QAction("Hide Ava", parent=menu)
    quit_action = QAction("Quit", parent=menu)

    show_action.triggered.connect(lambda: _show_window(window))
    hide_action.triggered.connect(window.hide)
    quit_action.triggered.connect(app.quit)

    menu.addAction(show_action)
    menu.addAction(hide_action)
    menu.addSeparator()
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: _handle_tray_activated(reason, window))
    tray.show()
    return tray


def _show_window(window) -> None:
    window.show()
    window.raise_()
    window.requestActivate()


def _handle_tray_activated(reason, window) -> None:
    if reason == QSystemTrayIcon.Trigger:
        if window.isVisible():
            window.hide()
        else:
            _show_window(window)


def run_ui(context: BootstrapContext) -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName(context.settings.app_name)
    icon_path = Path(__file__).with_name("qml") / "ava.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        app.setWindowIcon(_create_tray_icon())

    engine = QQmlApplicationEngine()
    app_state = QtAssistantState(context.state, context.settings)
    history_model = HistoryListModel(context.journal)
    bridge = UiBridge(context.controller, app_state, history_model)

    engine.rootContext().setContextProperty("appState", app_state)
    engine.rootContext().setContextProperty("uiBridge", bridge)
    engine.rootContext().setContextProperty("historyModel", history_model)

    qml_path = Path(__file__).with_name("qml") / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    root_window = engine.rootObjects()[0]
    tray = _create_tray(root_window, app) if QSystemTrayIcon.isSystemTrayAvailable() else None

    if context.settings.ui_auto_close_ms > 0:
        QTimer.singleShot(context.settings.ui_auto_close_ms, app.quit)

    if tray is not None:
        app.aboutToQuit.connect(tray.hide)
    return app.exec()
