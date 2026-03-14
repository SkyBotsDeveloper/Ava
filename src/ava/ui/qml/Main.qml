import QtQuick
import QtQuick.Controls

Window {
    id: root
    width: shellMode === "orb" ? 142 : shellMode === "quick" ? 292 : 332
    height: shellMode === "orb" ? 146 : shellMode === "quick" ? 236 : 334
    visible: true
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    title: "Ava"

    property string shellMode: "orb"
    property string visualState: appState.muted ? "muted" : appState.status
    property real ambientPhase: 0
    property real audioPhase: 0
    property color accentColor: accentFor(visualState)
    property color panelTint: softAccentFor(visualState)

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
        property bool prominent: false

        implicitWidth: prominent ? 58 : 50
        implicitHeight: 30
        padding: 0

        contentItem: Text {
            text: control.text
            color: control.danger ? "#ffd0d0" : control.prominent ? "#f7fbff" : "#d6e4f5"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: "Bahnschrift"
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }

        background: Rectangle {
            radius: 15
            color: control.danger ? (control.down ? "#231218" : "#16111a") : control.prominent ? (control.down ? "#132238" : "#101d30") : (control.down ? "#101827" : "#0c1422")
            border.width: 1
            border.color: control.danger ? Qt.rgba(0.85, 0.28, 0.33, 0.55) : control.prominent ? Qt.rgba(0.46, 0.76, 1.0, 0.45) : Qt.rgba(0.58, 0.74, 0.92, 0.15)

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: parent.height / 2
                radius: parent.radius
                color: control.danger ? Qt.rgba(1.0, 0.64, 0.64, 0.05) : Qt.rgba(0.93, 0.98, 1.0, control.prominent ? 0.06 : 0.03)
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"

        Rectangle {
            id: connectorStem

            anchors.horizontalCenter: parent.horizontalCenter
            y: 92
            width: shellMode === "full" ? 18 : 14
            height: shellMode === "orb" ? 0 : 34
            radius: width / 2
            color: root.accentColor
            opacity: shellMode === "full" ? 0.15 : 0.1
            visible: shellMode !== "orb"

            Behavior on height {
                NumberAnimation {
                    duration: 160
                }
            }
        }

        Rectangle {
            id: connectorDockAura

            anchors.horizontalCenter: parent.horizontalCenter
            y: 102
            width: shellMode === "full" ? 120 : 108
            height: shellMode === "orb" ? 0 : 34
            radius: 17
            color: root.accentColor
            opacity: shellMode === "full" ? 0.08 : 0.06
            visible: shellMode !== "orb"
        }

        Rectangle {
            id: connectorDock

            anchors.horizontalCenter: parent.horizontalCenter
            y: 106
            width: shellMode === "full" ? 112 : 100
            height: shellMode === "orb" ? 0 : 28
            radius: 14
            color: "#09121d"
            border.width: shellMode === "orb" ? 0 : 1
            border.color: Qt.rgba(0.72, 0.84, 1.0, 0.08)
            visible: shellMode !== "orb"
        }

        Rectangle {
            id: panelAura

            anchors.horizontalCenter: parent.horizontalCenter
            y: 116
            width: shellMode === "full" ? 320 : 282
            height: shellMode === "full" ? 208 : 112
            radius: shellMode === "full" ? 32 : 24
            color: root.accentColor
            opacity: shellMode === "orb" ? 0 : 0.045
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
            y: 120
            width: shellMode === "full" ? 308 : 270
            height: shellMode === "full" ? 196 : 108
            radius: shellMode === "full" ? 28 : 22
            visible: shellMode !== "orb"
            opacity: shellMode === "orb" ? 0 : 1
            color: "#07101a"
            border.width: 1
            border.color: Qt.rgba(0.64, 0.8, 1.0, 0.08)

            gradient: Gradient {
                GradientStop {
                    position: 0.0
                    color: Qt.rgba(0.045, 0.08, 0.13, 0.92)
                }
                GradientStop {
                    position: 1.0
                    color: Qt.rgba(0.025, 0.045, 0.08, 0.95)
                }
            }

            Behavior on opacity {
                NumberAnimation {
                    duration: 140
                }
            }

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: 8
                width: shellMode === "full" ? 88 : 74
                height: 4
                radius: 2
                color: Qt.rgba(0.86, 0.93, 1.0, 0.12)
            }

            Column {
                anchors.fill: parent
                anchors.margins: 14
                spacing: shellMode === "full" ? 11 : 10

                Row {
                    width: parent.width
                    height: 30
                    spacing: 10

                    Rectangle {
                        width: shellMode === "full" ? 96 : 92
                        height: 28
                        radius: 14
                        color: Qt.rgba(0.08, 0.14, 0.22, 0.7)
                        border.width: 1
                        border.color: Qt.rgba(0.6, 0.76, 0.96, 0.12)

                        Row {
                            anchors.centerIn: parent
                            spacing: 7

                            Rectangle {
                                width: 7
                                height: 7
                                radius: 3.5
                                anchors.verticalCenter: parent.verticalCenter
                                color: root.accentColor
                            }

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: root.statusLabel(root.visualState)
                                color: "#eef5ff"
                                font.family: "Bahnschrift"
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                            }
                        }
                    }

                    Item {
                        width: shellMode === "full" ? 46 : 24
                        height: 1
                    }

                    Row {
                        spacing: 6

                        GhostButton {
                            width: appState.muted ? 60 : 50
                            text: appState.muted ? "Unmute" : "Mute"
                            onClicked: uiBridge.toggleMute()
                        }

                        GhostButton {
                            width: 54
                            text: "Stop"
                            danger: true
                            prominent: true
                            onClicked: uiBridge.emergencyStop()
                        }

                        GhostButton {
                            width: shellMode === "full" ? 48 : 52
                            text: shellMode === "full" ? "Less" : "More"
                            onClicked: root.toggleFullPanel()
                        }
                    }
                }

                Text {
                    width: parent.width
                    text: root.statusMessage(root.visualState)
                    color: "#91a5bd"
                    font.family: "Segoe UI Variable"
                    font.pixelSize: 11
                }

                Rectangle {
                    width: parent.width
                    height: 48
                    radius: 15
                    color: Qt.rgba(0.08, 0.12, 0.19, 0.78)
                    border.width: 1
                    border.color: Qt.rgba(0.61, 0.75, 0.92, 0.05)

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
                            color: "#6f8397"
                            elide: Text.ElideRight
                            font.family: "Segoe UI Variable"
                            font.pixelSize: 9
                        }
                    }
                }

                Row {
                    width: parent.width
                    spacing: 8

                    TextField {
                        id: commandInput

                        width: parent.width - sendButton.width - 8
                        height: 38
                        placeholderText: "Type a command"
                        color: "#f4f8ff"
                        placeholderTextColor: "#62768e"
                        selectByMouse: true
                        font.family: "Segoe UI Variable"
                        font.pixelSize: 13
                        onAccepted: {
                            uiBridge.submitTextCommand(commandInput.text)
                            commandInput.clear()
                        }
                        onActiveFocusChanged: uiBridge.commandInputFocusChanged(activeFocus)

                        background: Rectangle {
                            radius: 18
                            color: Qt.rgba(0.07, 0.11, 0.18, 0.88)
                            border.width: 1
                            border.color: commandInput.activeFocus ? Qt.rgba(0.46, 0.78, 1.0, 0.7) : Qt.rgba(0.36, 0.5, 0.66, 0.18)
                        }
                    }

                    GhostButton {
                        id: sendButton

                        width: 62
                        text: "Send"
                        prominent: true
                        onClicked: {
                            uiBridge.submitTextCommand(commandInput.text)
                            commandInput.clear()
                        }
                    }
                }

                Text {
                    width: parent.width
                    visible: shellMode !== "full"
                    text: "Voice first. Type only when needed."
                    color: "#54677f"
                    font.family: "Segoe UI Variable"
                    font.pixelSize: 9
                }

                Rectangle {
                    width: parent.width
                    height: shellMode === "full" ? 64 : 0
                    radius: 16
                    color: Qt.rgba(0.05, 0.09, 0.15, 0.58)
                    border.width: shellMode === "full" ? 1 : 0
                    border.color: Qt.rgba(0.61, 0.75, 0.92, 0.05)
                    opacity: shellMode === "full" ? 0.88 : 0
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
                        spacing: 6

                        Text {
                            text: "Journal"
                            color: "#70849a"
                            font.family: "Bahnschrift"
                            font.pixelSize: 10
                        }

                        ListView {
                            id: historyList

                            width: parent.width
                            height: 36
                            clip: true
                            spacing: 4
                            interactive: false
                            model: historyModel

                            delegate: Column {
                                width: historyList.width
                                spacing: 1

                                Text {
                                    text: timestamp + "  " + resultStatus
                                    color: resultStatus === "canceled" ? "#d99090" : "#6cbfe0"
                                    font.family: "Segoe UI Variable"
                                    font.pixelSize: 8
                                }

                                Text {
                                    width: parent.width
                                    text: commandText
                                    color: "#bdd0e0"
                                    elide: Text.ElideRight
                                    font.family: "Segoe UI Variable"
                                    font.pixelSize: 10
                                }
                            }

                            Text {
                                anchors.centerIn: parent
                                visible: historyList.count === 0
                                text: "No activity yet."
                                color: "#556a80"
                                font.family: "Segoe UI Variable"
                                font.pixelSize: 9
                            }
                        }
                    }
                }
            }
        }

        Item {
            id: orb

            anchors.horizontalCenter: parent.horizontalCenter
            y: 8
            width: 124
            height: 124

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
                width: 110
                height: 110
                radius: 55
                color: root.accentColor
                opacity: appState.muted ? 0.045 : 0.085
                scale: 0.95 + Math.abs(Math.sin(root.ambientPhase)) * 0.05
            }

            Rectangle {
                anchors.centerIn: parent
                width: 126
                height: 126
                radius: 63
                color: root.accentColor
                opacity: root.visualState === "speaking" ? 0.065 : 0.028
                scale: 0.9 + Math.abs(Math.sin(root.ambientPhase + 1.3)) * 0.08
            }

            Item {
                anchors.centerIn: parent
                width: 116
                height: 116
                rotation: root.ambientPhase * 14
                opacity: appState.muted ? 0.1 : 0.24

                Repeater {
                    model: 3

                    Rectangle {
                        width: index === 0 ? 5 : 4
                        height: width
                        radius: width / 2
                        color: index === 0 ? "#eef7ff" : root.accentColor
                        x: parent.width / 2 - width / 2 + Math.cos(index / 3 * Math.PI * 2 + 0.5) * 50
                        y: parent.height / 2 - height / 2 + Math.sin(index / 3 * Math.PI * 2 + 0.5) * 50
                    }
                }
            }

            Item {
                anchors.centerIn: parent
                width: 122
                height: 122
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
                        x: parent.width / 2 - width / 2 + Math.cos(index / 8 * Math.PI * 2) * 52
                        y: parent.height / 2 - height / 2 + Math.sin(index / 8 * Math.PI * 2) * 52
                    }
                }
            }

            Item {
                anchors.centerIn: parent
                width: 124
                height: 124
                visible: root.visualState === "listening" || root.visualState === "speaking"

                Repeater {
                    model: 18

                    Rectangle {
                        property real intensity: (Math.sin(root.audioPhase + index * 0.34) + 1) / 2

                        width: 2
                        height: root.visualState === "speaking" ? 7 + intensity * 15 : 5 + intensity * 11
                        radius: 1
                        color: root.accentColor
                        opacity: root.visualState === "speaking" ? 0.88 : 0.62
                        x: parent.width / 2 - width / 2 + Math.cos(index / 18 * Math.PI * 2) * 53
                        y: parent.height / 2 - height / 2 + Math.sin(index / 18 * Math.PI * 2) * 53

                        transform: Rotation {
                            angle: index / 18 * 360 + 90
                            origin.x: width / 2
                            origin.y: height / 2
                        }
                    }
                }
            }

            Item {
                anchors.centerIn: parent
                width: 94
                height: 94
                rotation: root.ambientPhase * 9.5
                opacity: appState.muted ? 0.04 : 0.22

                Rectangle {
                    width: 28
                    height: 5
                    radius: 2.5
                    color: Qt.rgba(0.92, 0.97, 1.0, 0.18)
                    x: parent.width / 2 + 18
                    y: parent.height / 2 - 2
                    rotation: 24
                }
            }

            Rectangle {
                anchors.centerIn: parent
                width: 94
                height: 94
                radius: 47
                color: "transparent"
                border.width: 1
                border.color: Qt.rgba(0.86, 0.93, 1.0, 0.18)
            }

            Rectangle {
                anchors.centerIn: parent
                width: 78
                height: 78
                radius: 39
                color: "#0b1421"
                border.width: 1
                border.color: Qt.rgba(0.9, 0.96, 1.0, 0.18)

                gradient: Gradient {
                    GradientStop {
                        position: 0.0
                        color: Qt.rgba(0.08, 0.13, 0.2, 0.97)
                    }
                    GradientStop {
                        position: 1.0
                        color: Qt.rgba(0.025, 0.05, 0.1, 0.985)
                    }
                }
            }

            Rectangle {
                width: 30
                height: 6
                radius: 4
                color: Qt.rgba(0.93, 0.98, 1.0, 0.1)
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: 28
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
                    font.pixelSize: shellMode === "orb" ? 19 : 21
                    font.weight: Font.DemiBold
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.statusLabel(root.visualState)
                    color: "#9fb4ca"
                    font.family: "Segoe UI Variable"
                    font.pixelSize: 10
                    visible: shellMode !== "orb"
                }
            }

            Rectangle {
                anchors.right: parent.right
                anchors.rightMargin: 18
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 16
                width: 10
                height: 10
                radius: 5
                color: root.accentColor
                opacity: appState.muted ? 0.55 : 0.95

                Rectangle {
                    anchors.centerIn: parent
                    width: 18
                    height: 18
                    radius: 9
                    color: "transparent"
                    border.width: 1
                    border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.18)
                }
            }
        }
    }
}
