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
            title: "System snapshot"
            subtitle: "Current environment, latest patient event and gateway health"
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 4
            columnSpacing: 13
            rowSpacing: 13

            MetricTile {
                Layout.fillWidth: true
                theme: root.theme
                label: "Temperature"
                value: root.dataSource.temperature.toFixed(1)
                unit: "°C"
                note: "Ambient fused value"
                accentColor: root.theme.amber
                trendData: root.dataSource.tempHistory
            }

            MetricTile {
                Layout.fillWidth: true
                theme: root.theme
                label: "Humidity"
                value: root.dataSource.humidity.toFixed(1)
                unit: "%RH"
                note: "DHT22"
                accentColor: root.theme.cyan
                trendData: root.dataSource.humHistory
            }

            MetricTile {
                Layout.fillWidth: true
                theme: root.theme
                label: "Latest heart rate"

                value:
                    root.dataSource.vitalsValid
                    ? root.dataSource.heartRate.toString()
                    : "N/A"

                unit:
                    root.dataSource.vitalsValid
                    ? "BPM"
                    : ""

                note: "Latest patient event"
                accentColor: root.theme.red
                trendData: root.dataSource.hrHistory
            }

            MetricTile {
                Layout.fillWidth: true
                theme: root.theme
                label: "Latest SpO₂"

                value:
                    root.dataSource.vitalsValid
                    ? root.dataSource.spo2.toString()
                    : "N/A"

                unit:
                    root.dataSource.vitalsValid
                    ? "%"
                    : ""

                note: "Latest patient event"
                accentColor: root.theme.green
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 292
            spacing: 14

            SurfaceCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 1.5

                theme: root.theme

                accentColor:
                    root.dataSource.classification === "Non-asthma"
                    ? root.theme.green
                    : root.theme.amber

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 11

                    RowLayout {
                        Layout.fillWidth: true

                        Column {
                            Layout.fillWidth: true
                            spacing: 3

                            Text {
                                text: "LATEST PATIENT EVENT"
                                color: root.theme.text3
                                font.pixelSize: 9
                                font.weight: Font.DemiBold
                                font.letterSpacing: 1.2
                            }

                            Text {
                                text: root.dataSource.eventType
                                color: root.theme.text2
                                font.pixelSize: 12
                            }
                        }

                        Pill {
                            theme: root.theme
                            label: root.dataSource.audioQuality

                            dotColor:
                                root.dataSource.audioQuality === "GOOD"
                                ? root.theme.green
                                : root.theme.amber

                            pillColor:
                                root.dataSource.audioQuality === "GOOD"
                                ? root.theme.greenSoft
                                : root.theme.amberSoft
                        }
                    }

                    Text {
                        text: root.dataSource.classification

                        color:
                            root.dataSource.classification === "Non-asthma"
                            ? root.theme.green
                            : root.theme.amber

                        font.pixelSize: 32
                        font.weight: Font.Bold
                    }

                    Text {
                        text:
                            "Confidence "
                            + (
                                root.dataSource.modelScore
                                * 100
                            ).toFixed(1)
                            + "%"

                        color: root.theme.text2
                        font.pixelSize: 12
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 7
                        radius: 4

                        color:
                            root.theme.dark
                            ? "#253147"
                            : "#E6ECF4"

                        Rectangle {
                            width:
                                parent.width
                                * root.dataSource.modelScore

                            height: parent.height
                            radius: 4

                            color:
                                root.dataSource.classification === "Non-asthma"
                                ? root.theme.green
                                : root.theme.amber
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        Column {
                            spacing: 3
                            Text { text: "SESSION"; color: root.theme.text3; font.pixelSize: 9 }
                            Text { text: "#" + root.dataSource.sessionId; color: root.theme.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                        }

                        Item { Layout.fillWidth: true }

                        Column {
                            spacing: 3
                            Text { text: "EVENT TIME"; color: root.theme.text3; font.pixelSize: 9 }
                            Text { text: root.dataSource.eventTime; color: root.theme.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                        }

                        Item { Layout.fillWidth: true }

                        Column {
                            spacing: 3
                            Text { text: "NODE BATTERY"; color: root.theme.text3; font.pixelSize: 9 }
                            Text { text: root.dataSource.batteryNode + "%"; color: root.theme.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                        }
                    }
                }
            }

            SurfaceCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 1

                theme: root.theme
                accentColor: root.theme.blue

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 14

                    Text {
                        text: "GATEWAY HEALTH"
                        color: root.theme.text3
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
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
                        label: "Wi-Fi"

                        value:
                            root.dataSource.wifiConnected
                            ? root.dataSource.wifiRssi + " dBm"
                            : "Disconnected"

                        good: root.dataSource.wifiConnected
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "LTE"

                        value:
                            root.dataSource.lteRegistered
                            ? root.dataSource.lteRssi + " dBm"
                            : "Not registered"

                        good: root.dataSource.lteRegistered
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

                    Item {
                        Layout.fillHeight: true
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 60
                        radius: 12
                        color: root.theme.surface2

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 13

                            Column {
                                Layout.fillWidth: true

                                Text {
                                    text: "Gateway battery"
                                    color: root.theme.text3
                                    font.pixelSize: 9
                                }

                                Text {
                                    text: root.dataSource.batteryGateAvailable
                                          ? root.dataSource.batteryGate + "%"
                                          : "N/A"
                                    color: root.theme.text
                                    font.pixelSize: 18
                                    font.weight: Font.DemiBold
                                }
                            }

                            Rectangle {
                                width: 42
                                height: 42
                                radius: 12

                                color:
                                    !root.dataSource.batteryGateAvailable
                                    ? root.theme.surface2
                                    : root.dataSource.batteryGate > 20
                                    ? root.theme.greenSoft
                                    : root.theme.redSoft

                                Text {
                                    anchors.centerIn: parent
                                    text: "⚡"

                                    color:
                                        !root.dataSource.batteryGateAvailable
                                        ? root.theme.text3
                                        : root.dataSource.batteryGate > 20
                                        ? root.theme.green
                                        : root.theme.red

                                    font.pixelSize: 18
                                }
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 170
            spacing: 14

            SurfaceCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                theme: root.theme
                accentColor: root.theme.cyan

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 19
                    spacing: 12

                    Text {
                        text: "ENVIRONMENT"
                        color: root.theme.text3
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        Column {
                            Layout.fillWidth: true
                            Text { text: "Pressure"; color: root.theme.text3; font.pixelSize: 9 }
                            Text { text: root.dataSource.pressure.toFixed(1) + " hPa"; color: root.theme.text; font.pixelSize: 17; font.weight: Font.DemiBold }
                        }

                        Column {
                            Layout.fillWidth: true
                            Text { text: "TVOC"; color: root.theme.text3; font.pixelSize: 9 }
                            Text { text: root.dataSource.tvoc + " ppb"; color: root.theme.text; font.pixelSize: 17; font.weight: Font.DemiBold }
                        }

                        Column {
                            Layout.fillWidth: true
                            Text { text: "eCO₂"; color: root.theme.text3; font.pixelSize: 9 }
                            Text { text: root.dataSource.eco2 + " ppm"; color: root.theme.text; font.pixelSize: 17; font.weight: Font.DemiBold }
                        }
                    }
                }
            }

            SurfaceCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                theme: root.theme
                accentColor: root.theme.purple

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 19
                    spacing: 12

                    Text {
                        text: "SENSOR HEALTH"
                        color: root.theme.text3
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        SensorChip { theme: root.theme; sensorName: "DHT22"; ok: root.dataSource.dhtValid }
                        SensorChip { theme: root.theme; sensorName: "BMP280"; ok: root.dataSource.bmpValid }
                        SensorChip { theme: root.theme; sensorName: "SGP30"; ok: root.dataSource.sgpValid }
                        SensorChip { theme: root.theme; sensorName: "GPS"; ok: root.dataSource.gpsValid }
                    }
                }
            }
        }
    }
}
