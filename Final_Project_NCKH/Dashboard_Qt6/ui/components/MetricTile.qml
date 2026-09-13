import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    required property var theme

    property string label: ""
    property string value: ""
    property string unit: ""
    property string note: ""
    property color accentColor: root.theme.blue
    property var trendData: []

    radius: 17
    color: root.theme.surface

    border.width: 1
    border.color: root.theme.border

    implicitHeight: 150

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 17
        spacing: 3

        RowLayout {
            Layout.fillWidth: true

            Rectangle {
                width: 9
                height: 9
                radius: 5
                color: root.accentColor
            }

            Text {
                Layout.fillWidth: true
                text: root.label
                color: root.theme.text2
                font.pixelSize: 12
                font.weight: Font.DemiBold
            }
        }

        Row {
            Layout.topMargin: 7
            spacing: 5

            Text {
                text: root.value
                color: root.theme.text
                font.pixelSize: 29
                font.weight: Font.DemiBold
            }

            Text {
                visible: root.unit.length > 0
                text: root.unit
                color: root.theme.text2
                font.pixelSize: 12
                anchors.baseline: parent.children[0].baseline
            }
        }

        Text {
            text: root.note
            color: root.theme.text3
            font.pixelSize: 11
        }

        Item {
            Layout.fillHeight: true
        }

        Sparkline {
            visible: root.trendData.length > 1
            Layout.fillWidth: true
            Layout.preferredHeight: 32
            values: root.trendData
            lineColor: root.accentColor
        }
    }
}
