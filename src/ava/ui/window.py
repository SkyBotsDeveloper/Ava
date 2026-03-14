from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from ava.app.bootstrap import BootstrapContext
from ava.ui.app_state import QtAssistantState
from ava.ui.bridge import UiBridge
from ava.ui.history_model import HistoryListModel
from ava.ui.hotkeys import GlobalHotkeyManager
from ava.voice.service import VoiceRuntimeService

logger = logging.getLogger(__name__)


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


def _build_app_shortcuts(
    root_window,
    bridge,
    context: BootstrapContext,
    *,
    skip_global: dict[str, bool] | None = None,
) -> list[QShortcut]:
    shortcuts: list[QShortcut] = []
    bindings = [
        ("push_to_talk", context.settings.push_to_talk_hotkey, bridge.toggleManualListening),
        ("mute", context.settings.mute_hotkey, bridge.toggleMute),
        ("cancel", context.settings.emergency_stop_hotkey, bridge.emergencyStop),
    ]
    for key, sequence, handler in bindings:
        if skip_global and skip_global.get(key, False):
            continue
        shortcut = QShortcut(QKeySequence(sequence), root_window)
        shortcut.setContext(Qt.ApplicationShortcut)
        shortcut.activated.connect(handler)
        logger.info(
            "Application shortcut created",
            extra={
                "event": "app_shortcut_created",
                "shortcut_kind": key,
                "shortcut_sequence": sequence,
            },
        )
        shortcuts.append(shortcut)
    return shortcuts


def run_ui(context: BootstrapContext) -> int:
    QQuickStyle.setStyle("Basic")
    QQuickStyle.setFallbackStyle("Basic")
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
    voice_service = VoiceRuntimeService(
        settings=context.settings,
        state=context.state,
        journal=context.journal,
    )
    voice_service.start()
    bridge = UiBridge(context.controller, app_state, history_model, voice_service)

    engine.rootContext().setContextProperty("appState", app_state)
    engine.rootContext().setContextProperty("uiBridge", bridge)
    engine.rootContext().setContextProperty("historyModel", history_model)

    qml_path = Path(__file__).with_name("qml") / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    root_window = engine.rootObjects()[0]
    global_hotkeys = GlobalHotkeyManager()
    app.installNativeEventFilter(global_hotkeys)
    global_hotkeys.manualTriggerRequested.connect(bridge.toggleManualListening)
    global_hotkeys.muteRequested.connect(bridge.toggleMute)
    global_hotkeys.cancelRequested.connect(bridge.emergencyStop)
    global_bindings = global_hotkeys.register_defaults(
        push_to_talk=context.settings.push_to_talk_hotkey,
        mute=context.settings.mute_hotkey,
        cancel=context.settings.emergency_stop_hotkey,
    )
    bridge._app_shortcuts = _build_app_shortcuts(
        root_window,
        bridge,
        context,
        skip_global=global_bindings,
    )
    tray = _create_tray(root_window, app) if QSystemTrayIcon.isSystemTrayAvailable() else None

    if context.settings.ui_auto_close_ms > 0:
        QTimer.singleShot(context.settings.ui_auto_close_ms, app.quit)

    if tray is not None:
        app.aboutToQuit.connect(tray.hide)
    app.aboutToQuit.connect(global_hotkeys.unregister_all)
    app.aboutToQuit.connect(voice_service.shutdown)
    return app.exec()
