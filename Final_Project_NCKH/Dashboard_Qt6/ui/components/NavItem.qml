import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
    id: root

    required property var theme

    property bool selected: false
    property string navText: ""
    property string iconText: ""

    signal selectedByUser()

    Layout.fillWidth: true
    implicitHeight: 48
    hoverEnabled: true

    leftPadding: 0
    rightPadding: 0
    topPadding: 0
    bottomPadding: 0

    onClicked: root.selectedByUser()

    background: Rectangle {
        radius: 13

        color: {
            if (root.selected)
                return root.theme.selected

            if (root.hovered)
                return root.theme.hover

            return "transparent"
        }

        border.width: root.selected ? 1 : 0

        border.color:
            root.selected
            ? (root.theme.dark ? "#284F87" : "#C8DAF5")
            : "transparent"

        Behavior on color {
            ColorAnimation {
                duration: 120
            }
        }

        Rectangle {
            visible: root.selected
            width: 3
            height: 23
            radius: 2
            color: root.theme.blue

            anchors.left: parent.left
            anchors.leftMargin: 5
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    contentItem: RowLayout {
        spacing: 12

        Rectangle {
            width: 31
            height: 31
            radius: 9

            color:
                root.selected
                ? root.theme.blueSoft
                : "transparent"

            Text {
                anchors.centerIn: parent
                text: root.iconText

                color:
                    root.selected
                    ? root.theme.blue
                    : root.theme.text2

                font.pixelSize: 17
                font.weight: Font.DemiBold
            }
        }

        Text {
            Layout.fillWidth: true
            text: root.navText

            color:
                root.selected
                ? root.theme.text
                : root.theme.text2

            font.pixelSize: 13

            font.weight:
                root.selected
                ? Font.DemiBold
                : Font.Normal
        }

        Rectangle {
            visible: root.selected
            width: 6
            height: 6
            radius: 3
            color: root.theme.blue
        }
    }
}
