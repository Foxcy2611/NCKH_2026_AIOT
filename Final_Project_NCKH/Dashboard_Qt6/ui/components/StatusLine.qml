import QtQuick
import QtQuick.Layouts

RowLayout {
    id: root

    required property var theme

    property string label: ""
    property string value: ""
    property bool good: true
    property color statusColor:
        root.good ? root.theme.green : root.theme.red

    spacing: 10

    Rectangle {
        width: 8
        height: 8
        radius: 4
        color: root.statusColor
    }

    Text {
        Layout.fillWidth: true
        text: root.label
        color: root.theme.text2
        font.pixelSize: 12
    }

    Text {
        text: root.value
        color: root.theme.text
        font.pixelSize: 12
        font.weight: Font.DemiBold
    }
}
