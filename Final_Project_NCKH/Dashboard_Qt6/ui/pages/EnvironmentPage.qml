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
            title: "Environment"
            subtitle: "Current conditions measured by the gateway"
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 3
            columnSpacing: 14
            rowSpacing: 14

            MetricTile {
                Layout.fillWidth: true
                theme: root.theme
                label: "Temperature"
                value: root.dataSource.temperature.toFixed(1)
                unit: "°C"
                note: "DHT22 + BMP280 fusion"
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
                label: "Pressure"
                value: root.dataSource.pressure.toFixed(1)
                unit: "hPa"
                note: "BMP280"
                accentColor: root.theme.blue
            }

            MetricTile {
                Layout.fillWidth: true
                theme: root.theme
                label: "TVOC"
                value: root.dataSource.tvoc.toString()
                unit: "ppb"
                note: "SGP30"
                accentColor: root.theme.purple
            }

            MetricTile {
                Layout.fillWidth: true
                theme: root.theme
                label: "eCO₂"
                value: root.dataSource.eco2.toString()
                unit: "ppm"
                note: "CO₂-equivalent"
                accentColor: root.theme.green
            }
        }

        SurfaceCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 175
            theme: root.theme
            accentColor: root.theme.purple

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 13

                Text {
                    text: "SENSOR STATUS"
                    color: root.theme.text3
                    font.pixelSize: 9
                    font.weight: Font.DemiBold
                    font.letterSpacing: 1.2
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 10

                    SensorChip { theme: root.theme; sensorName: "DHT22"; ok: root.dataSource.dhtValid }
                    SensorChip { theme: root.theme; sensorName: "BMP280"; ok: root.dataSource.bmpValid }
                    SensorChip { theme: root.theme; sensorName: "SGP30"; ok: root.dataSource.sgpValid }
                    SensorChip { theme: root.theme; sensorName: "GPS"; ok: root.dataSource.gpsValid }
                }

                Text {
                    text:
                        "Temperature falls back to the remaining valid source if one sensor fails."

                    color: root.theme.text2
                    font.pixelSize: 11
                }
            }
        }
    }
}
