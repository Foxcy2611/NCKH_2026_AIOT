import QtQuick

Rectangle {
    id: root

    required property var theme

    property string sensorName: ""
    property bool ok: true

    implicitHeight: 36
    implicitWidth: 118
    radius: 11

    color:
        root.ok
        ? root.theme.greenSoft
        : root.theme.redSoft

    border.width: 1

    border.color:
        root.ok
        ? (root.theme.dark ? "#255848" : "#CDEFE1")
        : (root.theme.dark ? "#66303A" : "#F8CCD2")

    Row {
        anchors.centerIn: parent
        spacing: 7

        Rectangle {
            width: 7
            height: 7
            radius: 4
            color: root.ok ? root.theme.green : root.theme.red
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: root.sensorName
            color: root.theme.text
            font.pixelSize: 11
            font.weight: Font.DemiBold
        }
    }
}
