import QtQuick
import QtQuick.Layouts

Item {
    id: root

    required property var theme

    property string label: ""
    property string value: ""
    property color valueColor: root.theme.text
    property bool showDivider: true

    implicitHeight: Math.max(labelText.implicitHeight, valueText.implicitHeight) + 17

    RowLayout {
        anchors.fill: parent
        anchors.bottomMargin: 1
        spacing: 16

        Text {
            id: labelText
            Layout.preferredWidth: 122
            Layout.alignment: Qt.AlignTop

            text: root.label
            color: root.theme.text3
            font.pixelSize: 11
        }

        Text {
            id: valueText
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop

            text: root.value.length > 0 ? root.value : "Not provided"
            color: root.value.length > 0 ? root.valueColor : root.theme.text3
            font.pixelSize: 12
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignRight
            wrapMode: Text.WordWrap
        }
    }

    Rectangle {
        visible: root.showDivider
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: root.theme.border
    }
}
