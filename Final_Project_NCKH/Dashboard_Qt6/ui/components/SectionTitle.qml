import QtQuick

Item {
    id: root

    required property var theme

    property string title: ""
    property string subtitle: ""

    implicitHeight: root.subtitle.length > 0 ? 54 : 34

    Column {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        spacing: 3

        Text {
            text: root.title
            color: root.theme.text
            font.pixelSize: 24
            font.weight: Font.DemiBold
        }

        Text {
            visible: root.subtitle.length > 0
            text: root.subtitle
            color: root.theme.text2
            font.pixelSize: 12
        }
    }
}
