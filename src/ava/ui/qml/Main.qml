import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Window {
    id: root
    width: panelOpen ? 332 : 138
    height: panelOpen ? 494 : 166
    visible: true
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    title: "Ava"

    property bool panelOpen: false
    property string visualState: appState.muted ? "muted" : appState.status

    function accentFor(stateKey) {
        if (stateKey === "listening")
            return "#7dd3fc"
        if (stateKey === "thinking")
            return "#60a5fa"
        if (stateKey === "speaking")
            return "#38bdf8"
        if (stateKey === "muted")
            return "#94a3b8"
        return "#cbd5e1"
    }

    function panelTone(stateKey) {
        if (stateKey === "listening")
            return "#0f1825"
        if (stateKey === "thinking")
            return "#101828"
        if (stateKey === "speaking")
            return "#0c1622"
        if (stateKey === "muted")
            return "#11161f"
        return "#0c1119"
    }

    function labelFor(stateKey) {
        if (stateKey === "listening")
            return "Listening"
        if (stateKey === "thinking")
            return "Thinking"
        if (stateKey === "speaking")
            return "Speaking"
        if (stateKey === "muted")
            return "Muted"
        return "Idle"
    }

    Behavior on width {
        NumberAnimation {
            duration: 160
            easing.type: Easing.OutCubic
        }
    }

    Behavior on height {
        NumberAnimation {
            duration: 160
            easing.type: Easing.OutCubic
        }
    }

    component ShellButton : Button {
        id: control

        property color fillColor: "#101826"
        property color strokeColor: "#1f2a37"
        property color textColor: "#e2e8f0"
        property bool danger: false

        implicitHeight: 30
        implicitWidth: 58
        padding: 0

        contentItem: Text {
            text: control.text
            color: control.danger ? "#fecaca" : control.textColor
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: "Segoe UI Variable"
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }

        background: Rectangle {
            radius: 11
            color: control.down ? Qt.darker(control.fillColor, 1.12) : control.fillColor
            border.width: 1
            border.color: control.danger ? "#7f1d1d" : control.strokeColor
        }
    }

    component StateChip : Rectangle {
        id: chip

        property string chipText: ""
        property bool active: false
        property color accent: "#7dd3fc"

        radius: 10
        height: 22
        implicitWidth: chipLabel.implicitWidth + 16
        color: active ? accent : "#101827"
        border.width: active ? 0 : 1
        border.color: active ? accent : "#1c2736"

        Text {
            id: chipLabel

            anchors.centerIn: parent
            text: chip.chipText
            color: active ? "#04111e" : "#94a3b8"
            font.family: "Segoe UI Variable"
            font.pixelSize: 10
            font.weight: Font.DemiBold
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"

        Column {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

            Item {
                width: parent.width
                height: 126

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    onPressed: mouse => {
                        if (mouse.button === Qt.LeftButton) {
                            root.startSystemMove()
                        }
                    }
                    onDoubleClicked: root.panelOpen = !root.panelOpen
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: 104
                    height: 104
                    radius: 52
                    color: root.accentFor(root.visualState)
                    opacity: root.visualState === "idle" ? 0.08 : 0.16
                    scale: root.visualState === "thinking" ? 0.99 : 1.0

                    SequentialAnimation on scale {
                        loops: Animation.Infinite
                        running: root.visualState === "listening" || root.visualState === "speaking"
                        NumberAnimation {
                            from: 0.96
                            to: 1.04
                            duration: 900
                            easing.type: Easing.InOutQuad
                        }
                        NumberAnimation {
                            from: 1.04
                            to: 0.96
                            duration: 900
                            easing.type: Easing.InOutQuad
                        }
                    }
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: 110
                    height: 110
                    radius: 55
                    color: "transparent"
                    border.width: 1
                    border.color: root.visualState === "thinking" ? "#7dd3fc" : "#223042"
                    opacity: root.visualState === "thinking" ? 0.86 : 0.28

                    RotationAnimation on rotation {
                        running: root.visualState === "thinking"
                        loops: Animation.Infinite
                        duration: 1700
                        from: 0
                        to: 360
                    }
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: 86
                    height: 86
                    radius: 43
                    color: "#0f1725"
                    border.width: 1
                    border.color: Qt.lighter(root.accentFor(root.visualState), 1.05)
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 1

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "AVA"
                        color: "#f8fafc"
                        font.family: "Segoe UI Variable"
                        font.pixelSize: 21
                        font.weight: Font.DemiBold
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.labelFor(root.visualState)
                        color: "#9fb3c8"
                        font.family: "Segoe UI Variable"
                        font.pixelSize: 11
                    }
                }

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    width: openButton.implicitWidth + 14
                    height: openButton.implicitHeight + 10
                    radius: 14
                    color: panelOpen ? "#0f1725" : "#0b1018"
                    border.width: 1
                    border.color: "#1b2534"
                    visible: true

                    ShellButton {
                        id: openButton

                        anchors.centerIn: parent
                        width: 62
                        text: root.panelOpen ? "Hide" : "Open"
                        fillColor: "#101826"
                        strokeColor: "#223247"
                        onClicked: root.panelOpen = !root.panelOpen
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: panelOpen ? panelLayout.implicitHeight + 24 : 0
                radius: 24
                color: root.panelTone(root.visualState)
                border.width: 1
                border.color: "#1a2434"
                opacity: panelOpen ? 1 : 0
                clip: true

                Behavior on opacity {
                    NumberAnimation {
                        duration: 120
                    }
                }

                Behavior on height {
                    NumberAnimation {
                        duration: 160
                        easing.type: Easing.OutCubic
                    }
                }

                ColumnLayout {
                    id: panelLayout

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 14
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true

                        Text {
                            text: "Ava shell"
                            color: "#e2e8f0"
                            font.family: "Segoe UI Variable"
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        ShellButton {
                            text: appState.muted ? "Unmute" : "Mute"
                            onClicked: uiBridge.toggleMute()
                        }

                        ShellButton {
                            text: "Stop"
                            danger: true
                            fillColor: "#1a1116"
                            onClicked: uiBridge.emergencyStop()
                        }
                    }

                    Row {
                        spacing: 6

                        StateChip {
                            chipText: "Idle"
                            active: appState.status === "idle" && !appState.muted
                        }

                        StateChip {
                            chipText: "Listening"
                            active: appState.status === "listening" && !appState.muted
                            accent: "#7dd3fc"
                        }

                        StateChip {
                            chipText: "Thinking"
                            active: appState.status === "thinking" && !appState.muted
                            accent: "#60a5fa"
                        }

                        StateChip {
                            chipText: "Speaking"
                            active: appState.status === "speaking" && !appState.muted
                            accent: "#38bdf8"
                        }

                        StateChip {
                            chipText: "Muted"
                            active: appState.muted
                            accent: "#94a3b8"
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        radius: 16
                        color: "#0f1724"
                        border.width: 1
                        border.color: "#1b2534"

                        Column {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 6

                            Text {
                                text: "Latest response"
                                color: "#64748b"
                                font.family: "Segoe UI Variable"
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                            }

                            Text {
                                width: parent.width
                                text: appState.lastResponse.length > 0 ? appState.lastResponse : "Ava ready."
                                color: "#f8fafc"
                                wrapMode: Text.WordWrap
                                font.family: "Segoe UI Variable"
                                font.pixelSize: 13
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Text {
                            text: "Text fallback"
                            color: "#cbd5e1"
                            font.family: "Segoe UI Variable"
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            TextField {
                                id: commandInput

                                Layout.fillWidth: true
                                placeholderText: "Type a command"
                                color: "#f8fafc"
                                placeholderTextColor: "#64748b"
                                selectByMouse: true
                                font.family: "Segoe UI Variable"
                                font.pixelSize: 13
                                onAccepted: {
                                    uiBridge.submitTextCommand(commandInput.text)
                                    commandInput.clear()
                                }
                                onActiveFocusChanged: uiBridge.commandInputFocusChanged(activeFocus)

                                background: Rectangle {
                                    radius: 14
                                    color: "#111827"
                                    border.width: 1
                                    border.color: commandInput.activeFocus ? "#60a5fa" : "#1f2a37"
                                }
                            }

                            ShellButton {
                                text: "Send"
                                fillColor: "#0f2137"
                                strokeColor: "#1d4ed8"
                                onClicked: {
                                    uiBridge.submitTextCommand(commandInput.text)
                                    commandInput.clear()
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        radius: 16
                        color: "#0f1724"
                        border.width: 1
                        border.color: "#1b2534"

                        Column {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8

                            Row {
                                spacing: 6

                                Text {
                                    text: "Recent activity"
                                    color: "#cbd5e1"
                                    font.family: "Segoe UI Variable"
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }

                                Text {
                                    text: "audit"
                                    color: "#64748b"
                                    font.family: "Segoe UI Variable"
                                    font.pixelSize: 10
                                }
                            }

                            ListView {
                                id: historyList

                                width: parent.width
                                height: 126
                                clip: true
                                spacing: 6
                                model: historyModel

                                delegate: Rectangle {
                                    width: historyList.width
                                    height: historyText.paintedHeight + 24
                                    radius: 12
                                    color: "#111827"
                                    border.width: 1
                                    border.color: "#172033"

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 9
                                        spacing: 4

                                        Row {
                                            spacing: 8

                                            Text {
                                                text: timestamp
                                                color: "#7dd3fc"
                                                font.family: "Segoe UI Variable"
                                                font.pixelSize: 10
                                                font.weight: Font.DemiBold
                                            }

                                            Text {
                                                text: resultStatus
                                                color: resultStatus === "canceled" ? "#fca5a5" : "#86efac"
                                                font.family: "Segoe UI Variable"
                                                font.pixelSize: 10
                                            }
                                        }

                                        Text {
                                            id: historyText

                                            width: parent.width
                                            text: commandText
                                            color: "#f8fafc"
                                            wrapMode: Text.WordWrap
                                            font.family: "Segoe UI Variable"
                                            font.pixelSize: 11
                                        }
                                    }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    visible: historyList.count === 0
                                    text: "No journal entries yet."
                                    color: "#64748b"
                                    font.family: "Segoe UI Variable"
                                    font.pixelSize: 11
                                }
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "Hotkeys: talk " + appState.pushToTalkHotkey + " | mute " + appState.muteHotkey + " | stop " + appState.emergencyStopHotkey
                        color: "#5b6b80"
                        wrapMode: Text.WordWrap
                        font.family: "Segoe UI Variable"
                        font.pixelSize: 10
                    }
                }
            }
        }
    }
}
