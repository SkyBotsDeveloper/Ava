import QtQuick
import QtQuick.Controls

Window {
    id: root
    width: shellMode === "orb" ? 144 : shellMode === "quick" ? 300 : 340
    height: shellMode === "orb" ? 146 : shellMode === "quick" ? 248 : 368
    visible: true
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    title: "Ava"

    property string shellMode: "orb"
    property string visualState: appState.muted ? "muted" : appState.status
    property real ambientPhase: 0
    property real audioPhase: 0

    function accentFor(stateKey) {
        if (stateKey === "listening")
            return "#78d6ff"
        if (stateKey === "thinking")
            return "#74a9ff"
        if (stateKey === "speaking")
            return "#49c2ff"
        if (stateKey === "muted")
            return "#8b97ab"
        return "#c8d7ea"
    }

    function softAccentFor(stateKey) {
        if (stateKey === "listening")
            return "#14344d"
        if (stateKey === "thinking")
            return "#172847"
        if (stateKey === "speaking")
            return "#0f3347"
        if (stateKey === "muted")
            return "#1b2230"
        return "#121c2c"
    }

    function statusLabel(stateKey) {
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

    function statusMessage(stateKey) {
        if (stateKey === "listening")
            return "Ava is hearing you."
        if (stateKey === "thinking")
            return "Ava is thinking."
        if (stateKey === "speaking")
            return "Ava is replying."
        if (stateKey === "muted")
            return "Voice output is muted."
        return "Standing by."
    }

    function toggleQuickPanel() {
        root.shellMode = root.shellMode === "orb" ? "quick" : "orb"
    }

    function toggleFullPanel() {
        root.shellMode = root.shellMode === "full" ? "quick" : "full"
    }

    NumberAnimation on ambientPhase {
        from: 0
        to: Math.PI * 2
        duration: 5400
        loops: Animation.Infinite
        running: !appState.muted
    }

    NumberAnimation on audioPhase {
        from: 0
        to: Math.PI * 2
        duration: root.visualState === "speaking" ? 960 : 1320
        loops: Animation.Infinite
        running: root.visualState === "listening" || root.visualState === "speaking"
    }

    Behavior on width {
        NumberAnimation {
            duration: 180
            easing.type: Easing.OutCubic
        }
    }

    Behavior on height {
        NumberAnimation {
            duration: 180
            easing.type: Easing.OutCubic
        }
    }

    component GhostButton : Button {
        id: control

        property color glowColor: "#6fcfff"
        property bool danger: false

        implicitWidth: 52
        implicitHeight: 30
        padding: 0

        contentItem: Text {
            text: control.text
            color: control.danger ? "#ffc7c7" : "#eef5ff"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: "Bahnschrift"
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }

        background: Rectangle {
            radius: 15
            color: control.down ? "#121b2a" : "#0d1523"
            border.width: 1
            border.color: control.danger ? "#8f2430" : Qt.rgba(0.58, 0.74, 0.92, 0.18)
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"

        Rectangle {
            id: connectorGlow

            anchors.horizontalCenter: parent.horizontalCenter
            y: 86
            width: 12
            height: shellMode === "orb" ? 0 : 26
            radius: 6
            color: root.accentFor(root.visualState)
            opacity: shellMode === "full" ? 0.18 : 0.12
            visible: shellMode !== "orb"

            Behavior on height {
                NumberAnimation {
                    duration: 160
                }
            }
        }

        Rectangle {
            id: panelAura

            anchors.horizontalCenter: parent.horizontalCenter
            y: 98
            width: shellMode === "full" ? 328 : 284
            height: shellMode === "full" ? 260 : 140
            radius: shellMode === "full" ? 34 : 28
            color: root.accentFor(root.visualState)
            opacity: shellMode === "orb" ? 0 : 0.06
            scale: shellMode === "orb" ? 0.92 : 1.0
            visible: shellMode !== "orb"

            Behavior on opacity {
                NumberAnimation {
                    duration: 160
                }
            }

            Behavior on scale {
                NumberAnimation {
                    duration: 180
                }
            }
        }

        Rectangle {
            id: panel

            anchors.horizontalCenter: parent.horizontalCenter
            y: 102
            width: shellMode === "full" ? 314 : 270
            height: shellMode === "full" ? 246 : 126
            radius: shellMode === "full" ? 30 : 26
            visible: shellMode !== "orb"
            opacity: shellMode === "orb" ? 0 : 1
            color: "#08101c"
            border.width: 1
            border.color: Qt.rgba(0.64, 0.8, 1.0, 0.12)

            gradient: Gradient {
                GradientStop {
                    position: 0.0
                    color: Qt.rgba(0.06, 0.1, 0.16, 0.96)
                }
                GradientStop {
                    position: 1.0
                    color: Qt.rgba(0.03, 0.06, 0.1, 0.97)
                }
            }

            Behavior on opacity {
                NumberAnimation {
                    duration: 140
                }
            }

            Column {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 12

                Row {
                    width: parent.width
                    spacing: 8

                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        anchors.verticalCenter: parent.verticalCenter
                        color: root.accentFor(root.visualState)
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.statusLabel(root.visualState)
                        color: "#eef5ff"
                        font.family: "Bahnschrift"
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }

                    Item {
                        width: shellMode === "full" ? 88 : 52
                        height: 1
                    }

                    GhostButton {
                        width: appState.muted ? 58 : 52
                        text: appState.muted ? "Unmute" : "Mute"
                        onClicked: uiBridge.toggleMute()
                    }

                    GhostButton {
                        width: 48
                        text: "Stop"
                        danger: true
                        onClicked: uiBridge.emergencyStop()
                    }

                    GhostButton {
                        width: shellMode === "full" ? 48 : 50
                        text: shellMode === "full" ? "Less" : "More"
                        onClicked: root.toggleFullPanel()
                    }
                }

                Text {
                    width: parent.width
                    text: root.statusMessage(root.visualState)
                    color: "#8295ac"
                    font.family: "Segoe UI Variable"
                    font.pixelSize: 11
                }

                Rectangle {
                    width: parent.width
                    height: 54
                    radius: 16
                    color: "#0d1523"
                    border.width: 1
                    border.color: Qt.rgba(0.61, 0.75, 0.92, 0.08)

                    Column {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 2

                        Text {
                            width: parent.width
                            text: appState.lastResponse.length > 0 ? appState.lastResponse : "Ava ready."
                            color: "#f4f8ff"
                            elide: Text.ElideRight
                            font.family: "Segoe UI Variable"
                            font.pixelSize: 12
                        }

                        Text {
                            width: parent.width
                            text: appState.lastCommand.length > 0 ? appState.lastCommand : "Voice-first fallback available."
                            color: "#5f7288"
                            elide: Text.ElideRight
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
                        height: 36
                        placeholderText: "Type a command"
                        color: "#f4f8ff"
                        placeholderTextColor: "#5f7288"
                        selectByMouse: true
                        font.family: "Segoe UI Variable"
                        font.pixelSize: 13
                        onAccepted: {
                            uiBridge.submitTextCommand(commandInput.text)
                            commandInput.clear()
                        }
                        onActiveFocusChanged: uiBridge.commandInputFocusChanged(activeFocus)

                        background: Rectangle {
                            radius: 16
                            color: "#101928"
                            border.width: 1
                            border.color: commandInput.activeFocus ? "#5dbdff" : "#1b2a3e"
                        }
                    }

                    GhostButton {
                        id: sendButton

                        width: 62
                        text: "Send"
                        onClicked: {
                            uiBridge.submitTextCommand(commandInput.text)
                            commandInput.clear()
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: shellMode === "full" ? 88 : 0
                    radius: 18
                    color: "#0c1422"
                    border.width: shellMode === "full" ? 1 : 0
                    border.color: Qt.rgba(0.61, 0.75, 0.92, 0.08)
                    opacity: shellMode === "full" ? 1 : 0
                    clip: true
                    visible: shellMode === "full"

                    Behavior on opacity {
                        NumberAnimation {
                            duration: 120
                        }
                    }

                    Column {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        Text {
                            text: "Recent actions"
                            color: "#8ea2b8"
                            font.family: "Bahnschrift"
                            font.pixelSize: 11
                        }

                        ListView {
                            id: historyList

                            width: parent.width
                            height: 54
                            clip: true
                            spacing: 6
                            interactive: false
                            model: historyModel

                            delegate: Column {
                                width: historyList.width
                                spacing: 1

                                Text {
                                    text: timestamp + "  " + resultStatus
                                    color: resultStatus === "canceled" ? "#ffb4b4" : "#7cd8ff"
                                    font.family: "Segoe UI Variable"
                                    font.pixelSize: 9
                                }

                                Text {
                                    width: parent.width
                                    text: commandText
                                    color: "#d9e6f4"
                                    elide: Text.ElideRight
                                    font.family: "Segoe UI Variable"
                                    font.pixelSize: 11
                                }
                            }

                            Text {
                                anchors.centerIn: parent
                                visible: historyList.count === 0
                                text: "No activity yet."
                                color: "#5f7288"
                                font.family: "Segoe UI Variable"
                                font.pixelSize: 10
                            }
                        }
                    }
                }
            }
        }

        Item {
            id: orb

            anchors.horizontalCenter: parent.horizontalCenter
            y: 10
            width: 126
            height: 126

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                onPressed: mouse => {
                    if (mouse.button === Qt.LeftButton) {
                        root.startSystemMove()
                    }
                }
                onClicked: root.toggleQuickPanel()
                onDoubleClicked: root.toggleFullPanel()
            }

            Rectangle {
                anchors.centerIn: parent
                width: 116
                height: 116
                radius: 58
                color: root.accentFor(root.visualState)
                opacity: appState.muted ? 0.06 : 0.12
                scale: 0.92 + Math.abs(Math.sin(root.ambientPhase)) * 0.08
            }

            Rectangle {
                anchors.centerIn: parent
                width: 130
                height: 130
                radius: 65
                color: root.accentFor(root.visualState)
                opacity: root.visualState === "speaking" ? 0.08 : 0.04
                scale: 0.88 + Math.abs(Math.sin(root.ambientPhase + 1.3)) * 0.1
            }

            Item {
                anchors.centerIn: parent
                width: 120
                height: 120
                rotation: root.ambientPhase * 16
                opacity: appState.muted ? 0.15 : 0.38

                Repeater {
                    model: 3

                    Rectangle {
                        width: index === 0 ? 5 : 4
                        height: width
                        radius: width / 2
                        color: index === 0 ? "#e5f3ff" : root.accentFor(root.visualState)
                        x: parent.width / 2 - width / 2 + Math.cos(index / 3 * Math.PI * 2 + 0.5) * 53
                        y: parent.height / 2 - height / 2 + Math.sin(index / 3 * Math.PI * 2 + 0.5) * 53
                    }
                }
            }

            Item {
                anchors.centerIn: parent
                width: 124
                height: 124
                visible: root.visualState === "thinking"
                rotation: root.ambientPhase * 57.2958

                Repeater {
                    model: 8

                    Rectangle {
                        width: index % 2 === 0 ? 7 : 5
                        height: width
                        radius: width / 2
                        color: index % 2 === 0 ? "#7dd3fc" : "#7ba6ff"
                        opacity: index % 2 === 0 ? 0.95 : 0.55
                        x: parent.width / 2 - width / 2 + Math.cos(index / 8 * Math.PI * 2) * 54
                        y: parent.height / 2 - height / 2 + Math.sin(index / 8 * Math.PI * 2) * 54
                    }
                }
            }

            Item {
                anchors.centerIn: parent
                width: 128
                height: 128
                visible: root.visualState === "listening" || root.visualState === "speaking"

                Repeater {
                    model: 14

                    Rectangle {
                        property real intensity: Math.abs(Math.sin(root.audioPhase + index * 0.42))

                        width: 3
                        height: root.visualState === "speaking" ? 10 + intensity * 14 : 8 + intensity * 10
                        radius: 1.5
                        color: root.accentFor(root.visualState)
                        opacity: root.visualState === "speaking" ? 0.85 : 0.58
                        x: parent.width / 2 - width / 2 + Math.cos(index / 14 * Math.PI * 2) * 55
                        y: parent.height / 2 - height / 2 + Math.sin(index / 14 * Math.PI * 2) * 55

                        transform: Rotation {
                            angle: index / 14 * 360 + 90
                            origin.x: width / 2
                            origin.y: height / 2
                        }
                    }
                }
            }

            Rectangle {
                anchors.centerIn: parent
                width: 98
                height: 98
                radius: 49
                color: "transparent"
                border.width: 1
                border.color: Qt.rgba(0.83, 0.91, 1.0, 0.22)
            }

            Rectangle {
                anchors.centerIn: parent
                width: 82
                height: 82
                radius: 41
                color: "#0b1421"
                border.width: 1
                border.color: Qt.rgba(0.9, 0.96, 1.0, 0.22)

                gradient: Gradient {
                    GradientStop {
                        position: 0.0
                        color: Qt.rgba(0.09, 0.15, 0.23, 0.96)
                    }
                    GradientStop {
                        position: 1.0
                        color: Qt.rgba(0.03, 0.06, 0.11, 0.98)
                    }
                }
            }

            Rectangle {
                width: 34
                height: 8
                radius: 4
                color: Qt.rgba(0.93, 0.98, 1.0, 0.12)
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: 24
                rotation: -18
            }

            Column {
                anchors.centerIn: parent
                spacing: 1

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "AVA"
                    color: "#f8fbff"
                    font.family: "Bahnschrift"
                    font.pixelSize: shellMode === "orb" ? 20 : 22
                    font.weight: Font.DemiBold
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.statusLabel(root.visualState)
                    color: "#9fb4ca"
                    font.family: "Segoe UI Variable"
                    font.pixelSize: 11
                    visible: shellMode !== "orb"
                }
            }

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                width: 34
                height: 14
                radius: 7
                color: "#0c1320"
                border.width: 1
                border.color: Qt.rgba(0.61, 0.75, 0.92, 0.12)

                Row {
                    anchors.centerIn: parent
                    spacing: 4

                    Rectangle {
                        width: 5
                        height: 5
                        radius: 2.5
                        color: root.accentFor(root.visualState)
                    }

                    Rectangle {
                        width: 11
                        height: 2
                        radius: 1
                        color: Qt.rgba(0.86, 0.93, 1.0, 0.35)
                    }
                }
            }
        }
    }
}
