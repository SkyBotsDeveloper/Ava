import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Window {
    id: root
    visible: true
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    title: "Ava"

    property string shellMode: "orb"
    property string visualState: appState.muted ? "muted" : appState.status
    property real ambientPhase: 0
    property real wavePhase: 0

    readonly property bool panelVisible: shellMode !== "orb"
    readonly property bool fullPanel: shellMode === "full"
    readonly property int shellPadding: 18
    readonly property int panelOverlap: panelVisible ? 28 : 0
    readonly property int orbSceneWidth: 162
    readonly property int orbSceneHeight: 154
    readonly property int compactPanelWidth: 336
    readonly property int fullPanelWidth: 392
    readonly property int panelTargetWidth: fullPanel ? fullPanelWidth : compactPanelWidth
    readonly property color accentColor: accentFor(visualState)
    readonly property color panelTint: softAccentFor(visualState)

    width: shellPadding * 2 + Math.max(orbSceneWidth, panelVisible ? panelTargetWidth : 0)
    height: shellPadding * 2 + orbSceneHeight + (panelVisible ? panelStack.implicitHeight - panelOverlap : 0)

    function accentFor(stateKey) {
        if (stateKey === "listening")
            return "#7ad9ff"
        if (stateKey === "thinking")
            return "#81adff"
        if (stateKey === "speaking")
            return "#54c8ff"
        if (stateKey === "muted")
            return "#8f9eb2"
        return "#d4e0f1"
    }

    function softAccentFor(stateKey) {
        if (stateKey === "listening")
            return "#153147"
        if (stateKey === "thinking")
            return "#182844"
        if (stateKey === "speaking")
            return "#112f43"
        if (stateKey === "muted")
            return "#1d2430"
        return "#131b28"
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

    function toggleCompactPanel() {
        root.shellMode = root.shellMode === "orb" ? "compact" : "orb"
    }

    function toggleFullPanel() {
        root.shellMode = root.shellMode === "full" ? "compact" : "full"
    }

    NumberAnimation on ambientPhase {
        from: 0
        to: Math.PI * 2
        duration: 6200
        loops: Animation.Infinite
        running: !appState.muted
    }

    NumberAnimation on wavePhase {
        from: 0
        to: Math.PI * 2
        duration: visualState === "speaking" ? 860 : 1260
        loops: Animation.Infinite
        running: visualState === "listening" || visualState === "speaking"
    }

    Behavior on width {
        NumberAnimation {
            duration: 190
            easing.type: Easing.OutCubic
        }
    }

    Behavior on height {
        NumberAnimation {
            duration: 190
            easing.type: Easing.OutCubic
        }
    }

    component ControlButton : Button {
        id: control

        property string tone: "neutral"

        hoverEnabled: true
        implicitWidth: Math.max(54, label.implicitWidth + 24)
        implicitHeight: 36
        padding: 0

        contentItem: Text {
            id: label

            text: control.text
            color: tone === "danger" ? "#ffd5d5" : tone === "accent" ? "#f6fbff" : "#d6e4f3"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: "Bahnschrift"
            font.pixelSize: 12
            font.weight: Font.DemiBold
            renderType: Text.NativeRendering
        }

        background: Rectangle {
            radius: 18
            color: tone === "danger"
                ? (control.down ? "#251218" : control.hovered ? "#19131b" : "#161017")
                : tone === "accent"
                    ? (control.down ? "#14253a" : control.hovered ? "#12253b" : "#102033")
                    : (control.down ? "#101926" : control.hovered ? "#0f1a29" : "#0c1522")
            border.width: 1
            border.color: tone === "danger"
                ? Qt.rgba(0.83, 0.26, 0.32, control.hovered ? 0.64 : 0.56)
                : tone === "accent"
                    ? Qt.rgba(0.48, 0.77, 1.0, control.hovered ? 0.56 : 0.46)
                    : Qt.rgba(0.58, 0.72, 0.9, control.hovered ? 0.24 : 0.17)

            Rectangle {
                anchors.centerIn: parent
                width: parent.width + 10
                height: parent.height + 10
                radius: parent.radius + 5
                color: tone === "danger" ? "#c03645" : tone === "accent" ? root.accentColor : "#6a88ac"
                opacity: tone === "danger" ? 0.06 : tone === "accent" ? 0.08 : 0.03
                visible: control.hovered || control.down
                z: -1
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: parent.height / 2
                radius: parent.radius
                color: tone === "danger" ? Qt.rgba(1.0, 0.62, 0.62, 0.04) : tone === "accent" ? Qt.rgba(0.92, 0.98, 1.0, 0.06) : Qt.rgba(0.92, 0.98, 1.0, 0.03)
            }
        }
    }

    component StatusPill : Rectangle {
        implicitWidth: statusRow.implicitWidth + 20
        implicitHeight: 36
        radius: 18
        color: Qt.rgba(0.09, 0.15, 0.23, 0.68)
        border.width: 1
        border.color: Qt.rgba(0.62, 0.77, 0.97, 0.1)

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: root.panelTint
            opacity: 0.08
        }

        Row {
            id: statusRow

            anchors.centerIn: parent
            spacing: 8

            Rectangle {
                width: 8
                height: 8
                radius: 4
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

    Rectangle {
        anchors.fill: parent
        color: "transparent"

        Item {
            id: shellScene

            anchors.centerIn: parent
            width: Math.max(root.orbSceneWidth, root.panelVisible ? panelStack.implicitWidth : 0)
            height: root.orbSceneHeight + (root.panelVisible ? panelStack.implicitHeight - root.panelOverlap : 0)

            Item {
                id: orbScene

                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                width: root.orbSceneWidth
                height: root.orbSceneHeight

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton

                    onPressed: mouse => {
                        if (mouse.button === Qt.LeftButton) {
                            root.startSystemMove()
                        }
                    }

                    onClicked: root.toggleCompactPanel()
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: 150
                    height: 150
                    radius: 75
                    color: root.accentColor
                    opacity: appState.muted ? 0.03 : 0.018
                    scale: 0.9 + Math.abs(Math.sin(root.ambientPhase + 0.8)) * 0.1
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: 132
                    height: 132
                    radius: 66
                    color: root.accentColor
                    opacity: appState.muted ? 0.04 : visualState === "speaking" ? 0.085 : 0.05
                    scale: 0.95 + Math.abs(Math.sin(root.ambientPhase)) * 0.05
                }

                Item {
                    anchors.centerIn: parent
                    width: 130
                    height: 130
                    rotation: root.ambientPhase * 9
                    opacity: appState.muted ? 0.08 : 0.22

                    Repeater {
                        model: 3

                        Rectangle {
                            width: index === 0 ? 5 : 4
                            height: width
                            radius: width / 2
                            color: index === 0 ? "#f2f8ff" : root.accentColor
                            x: parent.width / 2 - width / 2 + Math.cos(index / 3 * Math.PI * 2 + 0.55) * 56
                            y: parent.height / 2 - height / 2 + Math.sin(index / 3 * Math.PI * 2 + 0.55) * 56
                        }
                    }
                }

                Item {
                    anchors.centerIn: parent
                    width: 126
                    height: 126
                    visible: root.visualState === "thinking"
                    rotation: root.ambientPhase * 57.2958

                    Repeater {
                        model: 8

                        Rectangle {
                            width: index % 2 === 0 ? 7 : 5
                            height: width
                            radius: width / 2
                            color: index % 2 === 0 ? "#89d7ff" : "#7fa9ff"
                            opacity: index % 2 === 0 ? 0.94 : 0.58
                            x: parent.width / 2 - width / 2 + Math.cos(index / 8 * Math.PI * 2) * 54
                            y: parent.height / 2 - height / 2 + Math.sin(index / 8 * Math.PI * 2) * 54
                        }
                    }
                }

                Item {
                    anchors.centerIn: parent
                    width: 132
                    height: 132
                    visible: root.visualState === "listening" || root.visualState === "speaking"

                    Repeater {
                        model: 20

                        Rectangle {
                            property real intensity: (Math.sin(root.wavePhase + index * 0.3) + 1) / 2

                            width: 2
                            height: root.visualState === "speaking" ? 7 + intensity * 18 : 5 + intensity * 11
                            radius: 1
                            color: root.accentColor
                            opacity: root.visualState === "speaking" ? 0.92 : 0.62
                            x: parent.width / 2 - width / 2 + Math.cos(index / 20 * Math.PI * 2) * 57
                            y: parent.height / 2 - height / 2 + Math.sin(index / 20 * Math.PI * 2) * 57

                            transform: Rotation {
                                angle: index / 20 * 360 + 90
                                origin.x: width / 2
                                origin.y: height / 2
                            }
                        }
                    }
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: 108
                    height: 108
                    radius: 54
                    color: "transparent"
                    border.width: 1
                    border.color: Qt.rgba(0.86, 0.93, 1.0, 0.16)
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: 118
                    height: 118
                    radius: 59
                    color: "transparent"
                    border.width: 1
                    border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, appState.muted ? 0.05 : 0.08)
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: 88
                    height: 88
                    radius: 44
                    color: "#0a1320"
                    border.width: 1
                    border.color: Qt.rgba(0.9, 0.96, 1.0, 0.17)

                    gradient: Gradient {
                        GradientStop {
                            position: 0.0
                            color: Qt.rgba(0.09, 0.15, 0.23, 0.97)
                        }

                        GradientStop {
                            position: 1.0
                            color: Qt.rgba(0.03, 0.06, 0.11, 0.985)
                        }
                    }
                }

                Rectangle {
                    width: 42
                    height: 7
                    radius: 4
                    color: Qt.rgba(0.94, 0.98, 1.0, 0.11)
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: 26
                    rotation: -20
                }

                Rectangle {
                    width: 28
                    height: 5
                    radius: 3
                    color: Qt.rgba(0.92, 0.98, 1.0, 0.07)
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: 36
                    rotation: -18
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 2

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "AVA"
                        color: "#f8fbff"
                        font.family: "Bahnschrift"
                        font.pixelSize: root.panelVisible ? 23 : 21
                        font.weight: Font.DemiBold
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.statusLabel(root.visualState)
                        color: "#9db3cb"
                        font.family: "Segoe UI Variable"
                        font.pixelSize: 10
                        visible: root.panelVisible
                    }
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.rightMargin: 24
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 20
                    width: 11
                    height: 11
                    radius: 5.5
                    color: root.accentColor
                    opacity: appState.muted ? 0.58 : 0.98

                    Rectangle {
                        anchors.centerIn: parent
                        width: 19
                        height: 19
                        radius: 9.5
                        color: "transparent"
                        border.width: 1
                        border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.18)
                    }
                }
            }

            Item {
                id: panelStack

                anchors.top: orbScene.bottom
                anchors.topMargin: -root.panelOverlap
                anchors.horizontalCenter: parent.horizontalCenter
                visible: root.panelVisible
                implicitWidth: root.panelTargetWidth
                implicitHeight: bridgeHalo.implicitHeight + panelCard.implicitHeight + 12
                width: implicitWidth
                height: implicitHeight

                Rectangle {
                    id: bridgeHalo

                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    implicitWidth: root.fullPanel ? 168 : 148
                    implicitHeight: 42
                    width: implicitWidth
                    height: implicitHeight
                    radius: 21
                    color: root.accentColor
                    opacity: 0.055
                }

                Rectangle {
                    anchors.top: parent.top
                    anchors.topMargin: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: root.fullPanel ? 126 : 110
                    height: 24
                    radius: 12
                    color: "#0a1320"
                    border.width: 1
                    border.color: Qt.rgba(0.72, 0.85, 1.0, 0.08)
                }

                Rectangle {
                    anchors.top: parent.top
                    anchors.topMargin: 24
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: root.panelTargetWidth + 10
                    height: panelCard.height + 10
                    radius: panelCard.radius + 5
                    color: root.accentColor
                    opacity: 0.038
                }

                Rectangle {
                    id: panelCard

                    anchors.top: parent.top
                    anchors.topMargin: 18
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: root.panelTargetWidth
                    implicitHeight: panelContent.implicitHeight + 34
                    height: implicitHeight
                    radius: root.fullPanel ? 30 : 26
                    color: "#07101a"
                    border.width: 1
                    border.color: Qt.rgba(0.64, 0.8, 1.0, 0.08)

                    gradient: Gradient {
                        GradientStop {
                            position: 0.0
                            color: Qt.rgba(0.05, 0.085, 0.135, 0.95)
                        }

                        GradientStop {
                            position: 1.0
                            color: Qt.rgba(0.022, 0.04, 0.075, 0.97)
                        }
                    }

                    Rectangle {
                        anchors.fill: parent
                        radius: parent.radius
                        color: root.panelTint
                        opacity: root.visualState === "idle" ? 0.06 : 0.1
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: parent.height * 0.46
                        radius: parent.radius
                        color: Qt.rgba(0.92, 0.98, 1.0, 0.028)
                    }

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.bottom
                        anchors.topMargin: -8
                        width: parent.width - 34
                        height: 26
                        radius: 13
                        color: root.accentColor
                        opacity: 0.025
                        z: -1
                    }

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 10
                        width: root.fullPanel ? 92 : 74
                        height: 4
                        radius: 2
                        color: Qt.rgba(0.9, 0.96, 1.0, 0.12)
                    }

                    ColumnLayout {
                        id: panelContent

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 18
                        anchors.topMargin: 24
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            StatusPill {
                                Layout.preferredWidth: implicitWidth
                            }

                            Item {
                                Layout.fillWidth: true
                            }

                            RowLayout {
                                spacing: 8

                                ControlButton {
                                    text: appState.muted ? "Unmute" : "Mute"
                                    tone: "neutral"
                                    onClicked: uiBridge.toggleMute()
                                }

                                ControlButton {
                                    text: "Stop"
                                    tone: "danger"
                                    onClicked: uiBridge.emergencyStop()
                                }

                                ControlButton {
                                    text: root.fullPanel ? "Compact" : "Expand"
                                    tone: "accent"
                                    onClicked: root.toggleFullPanel()
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.statusMessage(root.visualState)
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            color: "#9cafc5"
                            font.family: "Segoe UI Variable"
                            font.pixelSize: 12
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 52
                            radius: 18
                            color: Qt.rgba(0.08, 0.12, 0.19, 0.76)
                            border.width: 1
                            border.color: Qt.rgba(0.62, 0.77, 0.96, 0.05)

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 8

                                TextField {
                                    id: commandInput

                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 36
                                    placeholderText: "Type a command"
                                    color: "#f4f8ff"
                                    placeholderTextColor: "#63788f"
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
                                        color: Qt.rgba(0.07, 0.11, 0.18, 0.88)
                                        border.width: 1
                                        border.color: commandInput.activeFocus ? Qt.rgba(0.47, 0.79, 1.0, 0.72) : Qt.rgba(0.38, 0.51, 0.67, 0.18)
                                    }
                                }

                                ControlButton {
                                    text: "Send"
                                    tone: "accent"
                                    onClicked: {
                                        uiBridge.submitTextCommand(commandInput.text)
                                        commandInput.clear()
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 58
                            radius: 18
                            color: Qt.rgba(0.08, 0.12, 0.19, 0.54)
                            border.width: 1
                            border.color: Qt.rgba(0.62, 0.77, 0.96, 0.04)

                            Column {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 3

                                Text {
                                    width: parent.width
                                    text: appState.lastResponse.length > 0 ? appState.lastResponse : "Ava ready."
                                    color: "#edf5ff"
                                    elide: Text.ElideRight
                                    font.family: "Segoe UI Variable"
                                    font.pixelSize: 13
                                }

                                Text {
                                    width: parent.width
                                    text: appState.lastCommand.length > 0 ? appState.lastCommand : "Voice-first fallback available."
                                    color: "#6d8298"
                                    elide: Text.ElideRight
                                    font.family: "Segoe UI Variable"
                                    font.pixelSize: 10
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: !root.fullPanel
                            text: appState.manualVoiceReady
                                ? "Press " + appState.pushToTalkHotkey + " to talk. Text is fallback."
                                : "Voice first. Add Gemini key to enable talking. Text is fallback."
                            color: "#55697f"
                            font.family: "Segoe UI Variable"
                            font.pixelSize: 9
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: visible ? implicitHeight : 0
                            implicitHeight: 84
                            visible: root.fullPanel
                            radius: 20
                            color: Qt.rgba(0.05, 0.09, 0.15, 0.54)
                            border.width: 1
                            border.color: Qt.rgba(0.62, 0.77, 0.96, 0.04)

                            Column {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8

                                Row {
                                    width: parent.width
                                    spacing: 8

                                    Text {
                                        text: "Recent activity"
                                        color: "#72869b"
                                        font.family: "Bahnschrift"
                                        font.pixelSize: 10
                                    }

                                    Rectangle {
                                        width: 5
                                        height: 5
                                        radius: 2.5
                                        anchors.verticalCenter: parent.verticalCenter
                                        color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.5)
                                    }
                                }

                                ListView {
                                    id: historyList

                                    width: parent.width
                                    height: 46
                                    clip: true
                                    spacing: 4
                                    interactive: false
                                    model: historyModel

                                    delegate: Column {
                                        width: historyList.width
                                        spacing: 1

                                        Text {
                                            text: timestamp + "  " + resultStatus
                                            color: resultStatus === "canceled" ? "#cc8d8d" : "#6bb9d8"
                                            font.family: "Segoe UI Variable"
                                            font.pixelSize: 8
                                        }

                                        Text {
                                            width: parent.width
                                            text: commandText
                                            color: "#bdd0df"
                                            elide: Text.ElideRight
                                            font.family: "Segoe UI Variable"
                                            font.pixelSize: 10
                                        }
                                    }

                                    Text {
                                        anchors.centerIn: parent
                                        visible: historyList.count === 0
                                        text: "No activity yet."
                                        color: "#53687e"
                                        font.family: "Segoe UI Variable"
                                        font.pixelSize: 9
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
