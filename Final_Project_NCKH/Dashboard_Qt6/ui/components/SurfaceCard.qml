import QtQuick

Rectangle {
    id: root

    required property var theme

    property color accentColor: root.theme.blue

    radius: 18
    color: root.theme.surface

    border.width: 1
    border.color: root.theme.border

    Rectangle {
        width: 4
        height: 28
        radius: 2
        color: root.accentColor

        anchors.left: parent.left
        anchors.leftMargin: 1
        anchors.top: parent.top
        anchors.topMargin: 22
    }
}
