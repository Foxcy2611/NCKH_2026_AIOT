import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"

Flickable {
    id: root

    required property var theme
    required property var dataSource

    contentWidth: width
    contentHeight: contentColumn.implicitHeight + 52

    clip: true

    ScrollBar.vertical: ScrollBar {}

    ColumnLayout {
        id: contentColumn

        width: root.width - 56
        x: 28
        y: 12
        spacing: 17

        SectionTitle {
            Layout.fillWidth: true
            theme: root.theme
            title: "Gateway & Network"
            subtitle: "Connectivity, uplink and edge-device status"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 330
            spacing: 14

            SurfaceCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                theme: root.theme
                accentColor: root.theme.blue

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 17

                    Text {
                        text: "GATEWAY"
                        color: root.theme.text3
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "Gateway ID"
                        value: "#" + root.dataSource.gatewayId
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "Operating mode"
                        value: root.dataSource.operatingMode
                        statusColor: root.theme.blue
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "Current uplink"
                        value: root.dataSource.uplinkType
                        good: root.dataSource.uplinkType !== "NONE"
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "Gateway battery"
                        value: root.dataSource.batteryGate + "%"
                        good: root.dataSource.batteryGate > 20
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "MQTT broker"

                        value:
                            root.dataSource.mqttConnected
                            ? "Connected"
                            : "Disconnected"

                        good: root.dataSource.mqttConnected
                    }
                }
            }

            SurfaceCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                theme: root.theme
                accentColor: root.theme.cyan

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 17

                    Text {
                        text: "CONNECTIVITY"
                        color: root.theme.text3
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "Wi-Fi"

                        value:
                            root.dataSource.wifiConnected
                            ? "Connected"
                            : "Disconnected"

                        good: root.dataSource.wifiConnected
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "Wi-Fi RSSI"
                        value: root.dataSource.wifiRssi + " dBm"
                        good: root.dataSource.wifiConnected
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "LTE"

                        value:
                            root.dataSource.lteRegistered
                            ? "Registered"
                            : "Not registered"

                        good: root.dataSource.lteRegistered
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "LTE RSSI"
                        value: root.dataSource.lteRssi + " dBm"
                        good: root.dataSource.lteRegistered
                    }

                    Item {
                        Layout.fillHeight: true
                    }

                    Pill {
                        theme: root.theme
                        label: "Active uplink: " + root.dataSource.uplinkType
                        dotColor: root.theme.blue
                        pillColor: root.theme.blueSoft
                    }
                }
            }
        }
    }
}
