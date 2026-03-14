import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Window {
    id: root
    width: 360
    height: 520
    visible: true
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    title: "Ava"

    Rectangle {
        anchors.fill: parent
        radius: 28
        color: "#0d1117"
        border.color: "#2b3545"
        border.width: 1

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            onPressed: mouse => {
                if (mouse.button === Qt.LeftButton) {
                    root.startSystemMove()
                }
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 16

            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                width: 120
                height: 120
                radius: 60
                color: appState.muted ? "#2f2f2f" : "#112138"
                border.width: 2
                border.color: appState.muted ? "#6f6f6f" : "#7dd3fc"

                Column {
                    anchors.centerIn: parent
                    spacing: 4

                    Label {
                        text: "AVA"
                        color: "#f8fafc"
                        font.pixelSize: 24
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Label {
                        text: appState.status
                        color: "#94a3b8"
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }

            Label {
                text: "Voice-first, with safe fallback controls."
                color: "#cbd5e1"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 16
                color: "#101826"
                border.width: 1
                border.color: "#1e293b"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    Label {
                        text: "Last command"
                        color: "#94a3b8"
                    }

                    Label {
                        text: appState.lastCommand.length > 0 ? appState.lastCommand : "No command yet"
                        color: "#f8fafc"
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    Label {
                        text: "Last response"
                        color: "#94a3b8"
                    }

                    Label {
                        text: appState.lastResponse.length > 0 ? appState.lastResponse : "Ava ready"
                        color: "#f8fafc"
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            TextField {
                id: commandInput
                Layout.fillWidth: true
                placeholderText: "Type a fallback command"
                color: "#f8fafc"
                placeholderTextColor: "#64748b"
                selectByMouse: true
                onAccepted: {
                    uiBridge.submitTextCommand(commandInput.text)
                    commandInput.clear()
                }
                background: Rectangle {
                    radius: 14
                    color: "#111827"
                    border.width: 1
                    border.color: "#1d4ed8"
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Button {
                    Layout.fillWidth: true
                    text: "Send"
                    onClicked: {
                        uiBridge.submitTextCommand(commandInput.text)
                        commandInput.clear()
                    }
                }

                Button {
                    Layout.fillWidth: true
                    text: appState.muted ? "Unmute" : "Mute"
                    onClicked: uiBridge.toggleMute()
                }
            }

            Button {
                Layout.fillWidth: true
                text: "Emergency Stop"
                onClicked: uiBridge.emergencyStop()
            }

            Label {
                Layout.fillWidth: true
                text: "Hotkeys: Ctrl+Alt+A push-to-talk, Ctrl+Alt+M mute, Ctrl+Alt+Backspace stop"
                color: "#64748b"
                wrapMode: Text.WordWrap
            }
        }
    }
}
