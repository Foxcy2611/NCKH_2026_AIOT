import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    required property var theme
    required property var dataSource

    property int currentPage: 0

    signal themeToggle()

    color: root.theme.page

    function pageTitle() {
        switch (root.currentPage) {
        case 0: return "Overview"
        case 1: return "Patient monitoring"
        case 2: return "Environment"
        case 3: return "Gateway & Network"
        case 4: return "Location"
        default: return "Dashboard"
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 28
        anchors.rightMargin: 28
        spacing: 14

        Column {
            Layout.fillWidth: true
            spacing: 2

            Text {
                text: root.pageTitle()
                color: root.theme.text
                font.pixelSize: 18
                font.weight: Font.DemiBold
            }

            Text {
                text: "Respiratory edge monitoring • Frontend demo"
                color: root.theme.text3
                font.pixelSize: 10
            }
        }

        Pill {
            theme: root.theme

            label:
                root.dataSource.mqttConnected
                ? "MQTT Online"
                : "MQTT Offline"

            dotColor:
                root.dataSource.mqttConnected
                ? root.theme.green
                : root.theme.red
        }

        Pill {
            theme: root.theme
            label: root.dataSource.operatingMode
            dotColor: root.theme.blue
        }

        Button {
            id: themeButton

            implicitWidth: 42
            implicitHeight: 42
            hoverEnabled: true

            onClicked: root.themeToggle()

            background: Rectangle {
                radius: 12

                color:
                    themeButton.hovered
                    ? root.theme.hover
                    : root.theme.surface

                border.width: 1
                border.color: root.theme.border
            }

            contentItem: Text {
                text:
                    root.theme.dark
                    ? "☀"
                    : "☾"

                color: root.theme.text
                font.pixelSize: 17

                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
