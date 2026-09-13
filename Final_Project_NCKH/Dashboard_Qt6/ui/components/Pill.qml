import QtQuick

Rectangle {
    id: root

    required property var theme

    property string label: ""
    property color dotColor: root.theme.green
    property color pillColor: root.theme.surface2

    implicitWidth: row.implicitWidth + 22
    implicitHeight: 30

    radius: 15
    color: root.pillColor

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 7

        Rectangle {
            width: 7
            height: 7
            radius: 4
            color: root.dotColor
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: root.label
            color: root.theme.text2
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }
    }
}
