import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    required property var theme
    required property var dataSource

    property int currentPage: 0
    property string patientName: "Nguyễn Văn A"
    property string patientId: "Patient #001"
    property url ptitLogoSource: ""

    signal pageRequested(int pageIndex)

    color: root.theme.sidebar

    Rectangle {
        width: 1

        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right

        color: root.theme.border
    }

    ColumnLayout {
        anchors.fill: parent

        anchors.leftMargin: 18
        anchors.rightMargin: 18
        anchors.topMargin: 22
        anchors.bottomMargin: 14

        spacing: 5

        // ========================================================
        // PATIENT IDENTITY
        // ========================================================

        RowLayout {
            Layout.fillWidth: true
            Layout.bottomMargin: 24
            spacing: 11

            Rectangle {
                width: 43
                height: 43
                radius: 13
                color: root.theme.blueSoft

                Text {
                    anchors.centerIn: parent

                    text:
                        root.patientName.length > 0
                        ? root.patientName.charAt(0).toUpperCase()
                        : "P"

                    color: root.theme.blue
                    font.pixelSize: 19
                    font.weight: Font.Bold
                }
            }

            Column {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    width: parent.width
                    elide: Text.ElideRight
                    text: root.patientName
                    color: root.theme.text
                    font.pixelSize: 16
                    font.weight: Font.Bold
                }

                Text {
                    text: root.patientId
                    color: root.theme.text2
                    font.pixelSize: 10
                }
            }
        }

        Text {
            text: "WORKSPACE"
            color: root.theme.text3
            font.pixelSize: 9
            font.weight: Font.DemiBold
            font.letterSpacing: 1.4
            Layout.leftMargin: 9
            Layout.bottomMargin: 5
        }

        NavItem {
            theme: root.theme
            selected: root.currentPage === 0
            iconText: "⌂"
            navText: "Overview"
            onSelectedByUser: root.pageRequested(0)
        }

        NavItem {
            theme: root.theme
            selected: root.currentPage === 1
            iconText: "♥"
            navText: "Patient"
            onSelectedByUser: root.pageRequested(1)
        }

        NavItem {
            theme: root.theme
            selected: root.currentPage === 2
            iconText: "◈"
            navText: "Environment"
            onSelectedByUser: root.pageRequested(2)
        }

        NavItem {
            theme: root.theme
            selected: root.currentPage === 3
            iconText: "⌁"
            navText: "Gateway & Network"
            onSelectedByUser: root.pageRequested(3)
        }

        NavItem {
            theme: root.theme
            selected: root.currentPage === 4
            iconText: "⌖"
            navText: "Location"
            onSelectedByUser: root.pageRequested(4)
        }

        Item {
            Layout.fillHeight: true
        }

        // ========================================================
        // GATEWAY CARD
        // ========================================================

        Text {
            text: "GATEWAY"
            color: root.theme.text3
            font.pixelSize: 9
            font.weight: Font.DemiBold
            font.letterSpacing: 1.4
            Layout.leftMargin: 9
            Layout.bottomMargin: 4
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 104
            radius: 16

            color: root.theme.surface2

            border.width: 1
            border.color: root.theme.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 7

                RowLayout {
                    Layout.fillWidth: true

                    Rectangle {
                        width: 9
                        height: 9
                        radius: 5

                        color:
                            root.dataSource.mqttConnected
                            ? root.theme.green
                            : root.theme.red
                    }

                    Text {
                        Layout.fillWidth: true

                        text:
                            "Gateway #"
                            + root.dataSource.gatewayId

                        color: root.theme.text
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }

                    Text {
                        text:
                            root.dataSource.batteryGate
                            + "%"

                        color:
                            root.dataSource.batteryGate > 20
                            ? root.theme.text2
                            : root.theme.red

                        font.pixelSize: 11
                    }
                }

                RowLayout {
                    Layout.fillWidth: true

                    Text {
                        text: root.dataSource.operatingMode
                        color: root.theme.blue
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Text {
                        text: root.dataSource.uplinkType
                        color: root.theme.text2
                        font.pixelSize: 10
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 5
                    radius: 3

                    color:
                        root.theme.dark
                        ? "#263248"
                        : "#E4EAF2"

                    Rectangle {
                        width:
                            parent.width
                            * Math.min(
                                root.dataSource.batteryGate,
                                100
                            )
                            / 100

                        height: parent.height
                        radius: 3

                        color:
                            root.dataSource.batteryGate > 20
                            ? root.theme.green
                            : root.theme.red
                    }
                }
            }
        }

        // ========================================================
        // PTIT / TEAM
        // ========================================================

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 70
            Layout.topMargin: 5

            radius: 15

            color: root.theme.surface2

            border.width: 1
            border.color: root.theme.border

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 11
                anchors.rightMargin: 11
                spacing: 10

                Rectangle {
                    width: 45
                    height: 45
                    radius: 10
                    color: "#FFFFFF"

                    Image {
                        anchors.fill: parent
                        anchors.margins: 4

                        source: root.ptitLogoSource

                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }
                }

                Column {
                    Layout.fillWidth: true
                    spacing: 1

                    Text {
                        text: "PTIT"
                        color: root.theme.text
                        font.pixelSize: 12
                        font.weight: Font.Bold
                    }

                    Text {
                        text: "ARM-LAB"
                        color: root.theme.blue
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                    }

                    Text {
                        text: "NCKH 2026"
                        color: root.theme.text3
                        font.pixelSize: 9
                    }
                }
            }
        }
    }
}
