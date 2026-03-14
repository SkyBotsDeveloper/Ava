import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Window {
    id: root
    width: panelOpen ? 322 : 140
    height: panelOpen ? 448 : 170
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

    function glowStrength(stateKey) {
        if (stateKey === "listening")
            return 0.22
        if (stateKey === "thinking")
            return 0.26
        if (stateKey === "speaking")
            return 0.3
        if (stateKey === "muted")
            return 0.1
        return 0.12
    }

    function panelTone(stateKey) {
        if (stateKey === "listening")
            return "#0d1623"
        if (stateKey === "thinking")
            return "#0d1420"
        if (stateKey === "speaking")
            return "#0b1521"
        if (stateKey === "muted")
            return "#10151d"
        return "#0a1018"
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
            duration: 170
            easing.type: Easing.OutCubic
        }
    }

    Behavior on height {
        NumberAnimation {
            duration: 170
            easing.type: Easing.OutCubic
        }
    }

    component ShellButton : Button {
        id: control

        property color fillColor: "#101826"
        property color strokeColor: "#1d2a3b"
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
            color: control.down ? Qt.darker(control.fillColor, 1.15) : control.fillColor
            border.width: 1
            border.color: control.danger ? "#8b1e2a" : control.strokeColor
        }
    }

    component StateChip : Rectangle {
        id: chip

        property string chipText: ""
        property bool active: false
        property color accent: "#7dd3fc"

        radius: 10
        height: 21
        implicitWidth: chipLabel.implicitWidth + 14
        color: active ? accent : "#0e1725"
        border.width: active ? 0 : 1
        border.color: active ? accent : "#1b2535"

        Text {
            id: chipLabel

            anchors.centerIn: parent
            text: chip.chipText
            color: active ? "#03111d" : "#90a4bd"
            font.family: "Segoe UI Variable"
            font.pixelSize: 9
            font.weight: Font.DemiBold
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"

        Column {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            Item {
                width: parent.width
                height: 130

                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 8

                    Item {
                        id: orbStack

                        width: 124
                        height: 92

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
                            width: 116
                            height: 116
                            radius: 58
                            color: root.accentFor(root.visualState)
                            opacity: root.glowStrength(root.visualState)
                            scale: 0.92

                            SequentialAnimation on scale {
                                loops: Animation.Infinite
                                running: root.visualState === "listening" || root.visualState === "speaking"
                                NumberAnimation {
                                    from: 0.9
                                    to: 1.03
                                    duration: 950
                                    easing.type: Easing.InOutQuad
                                }
                                NumberAnimation {
                                    from: 1.03
                                    to: 0.9
                                    duration: 950
                                    easing.type: Easing.InOutQuad
                                }
                            }
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            width: 132
                            height: 132
                            radius: 66
                            color: root.accentFor(root.visualState)
                            opacity: root.visualState === "speaking" ? 0.08 : 0.04
                            scale: 0.88

                            SequentialAnimation on scale {
                                loops: Animation.Infinite
                                running: root.visualState === "thinking" || root.visualState === "speaking"
                                NumberAnimation {
                                    from: 0.86
                                    to: 1.05
                                    duration: 1600
                                    easing.type: Easing.OutQuad
                                }
                                NumberAnimation {
                                    from: 1.05
                                    to: 0.86
                                    duration: 1600
                                    easing.type: Easing.InQuad
                                }
                            }
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            width: 104
                            height: 104
                            radius: 52
                            color: "transparent"
                            border.width: 1
                            border.color: Qt.rgba(0.76, 0.88, 1.0, 0.25)
                        }

                        Item {
                            anchors.centerIn: parent
                            width: 122
                            height: 122
                            visible: root.visualState === "thinking"

                            RotationAnimation on rotation {
                                running: parent.visible
                                loops: Animation.Infinite
                                duration: 1800
                                from: 0
                                to: 360
                            }

                            Repeater {
                                model: 8

                                Rectangle {
                                    width: index % 2 === 0 ? 7 : 5
                                    height: width
                                    radius: width / 2
                                    color: index % 2 === 0 ? "#7dd3fc" : "#60a5fa"
                                    opacity: index % 2 === 0 ? 0.95 : 0.55
                                    x: parent.width / 2 - width / 2 + Math.cos(index / model * Math.PI * 2) * 54
                                    y: parent.height / 2 - height / 2 + Math.sin(index / model * Math.PI * 2) * 54
                                }
                            }
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            width: 86
                            height: 86
                            radius: 43
                            color: "#0c1523"
                            border.width: 1
                            border.color: Qt.lighter(root.accentFor(root.visualState), 1.08)
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
                    }

                    ShellButton {
                        width: 66
                        text: root.panelOpen ? "Hide" : "Open"
                        fillColor: "#101826"
                        strokeColor: "#223247"
                        onClicked: root.panelOpen = !root.panelOpen
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: panelOpen ? drawerContent.implicitHeight + 22 : 0
                radius: 22
                color: root.panelTone(root.visualState)
                border.width: 1
                border.color: "#172131"
                opacity: panelOpen ? 1 : 0
                clip: true

                Behavior on opacity {
                    NumberAnimation {
                        duration: 120
                    }
                }

                Behavior on height {
                    NumberAnimation {
                        duration: 170
                        easing.type: Easing.OutCubic
                    }
                }

                Column {
                    id: drawerContent

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    spacing: 10

                    Row {
                        width: parent.width
                        spacing: 8

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: appState.lastResponse.length > 0 ? appState.lastResponse : "Ava ready."
                            color: "#e2e8f0"
                            width: 156
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            wrapMode: Text.WordWrap
                            font.family: "Segoe UI Variable"
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }

                        Item {
                            width: 6
                            height: 1
                        }

                        ShellButton {
                            width: 68
                            text: appState.muted ? "Unmute" : "Mute"
                            onClicked: uiBridge.toggleMute()
                        }

                        ShellButton {
                            width: 56
                            text: "Stop"
                            danger: true
                            fillColor: "#181015"
                            onClicked: uiBridge.emergencyStop()
                        }
                    }

                    Flow {
                        width: parent.width
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
                        width: parent.width
                        height: 54
                        radius: 15
                        color: "#0f1724"
                        border.width: 1
                        border.color: "#1b2534"

                        Column {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 2

                            Text {
                                width: parent.width
                                text: appState.lastCommand.length > 0 ? appState.lastCommand : "Voice-first desktop agent"
                                color: "#f8fafc"
                                elide: Text.ElideRight
                                font.family: "Segoe UI Variable"
                                font.pixelSize: 12
                            }

                            Text {
                                width: parent.width
                                text: "Type if voice is unavailable."
                                color: "#64748b"
                                font.family: "Segoe UI Variable"
                                font.pixelSize: 10
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 8

                        TextField {
                            id: commandInput

                            width: parent.width - sendButton.width - 8
                            height: 34
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
                            id: sendButton

                            width: 60
                            text: "Send"
                            fillColor: "#0f2137"
                            strokeColor: "#1d4ed8"
                            onClicked: {
                                uiBridge.submitTextCommand(commandInput.text)
                                commandInput.clear()
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 108
                        radius: 15
                        color: "#0f1724"
                        border.width: 1
                        border.color: "#1b2534"

                        Column {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            Text {
                                text: "Recent"
                                color: "#8ea4bc"
                                font.family: "Segoe UI Variable"
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                            }

                            ListView {
                                id: historyList

                                width: parent.width
                                height: 72
                                clip: true
                                spacing: 6
                                interactive: false
                                model: historyModel

                                delegate: Column {
                                    width: historyList.width
                                    spacing: 2

                                    Text {
                                        text: timestamp + "  " + resultStatus
                                        color: resultStatus === "canceled" ? "#fca5a5" : "#7dd3fc"
                                        font.family: "Segoe UI Variable"
                                        font.pixelSize: 9
                                    }

                                    Text {
                                        width: parent.width
                                        text: commandText
                                        color: "#dbe5f0"
                                        elide: Text.ElideRight
                                        font.family: "Segoe UI Variable"
                                        font.pixelSize: 11
                                    }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    visible: historyList.count === 0
                                    text: "No activity yet."
                                    color: "#64748b"
                                    font.family: "Segoe UI Variable"
                                    font.pixelSize: 10
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
