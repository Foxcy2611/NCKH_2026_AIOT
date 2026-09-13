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
            title: "Latest patient event"
            subtitle: "Event-based measurements — not continuous realtime vitals"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 250
            spacing: 14

            SurfaceCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 1.3
                theme: root.theme

                accentColor:
                    root.dataSource.classification === "Normal"
                    ? root.theme.green
                    : root.theme.amber

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 10

                    Text {
                        text: "AI CLASSIFICATION"
                        color: root.theme.text3
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                    }

                    Text {
                        text: root.dataSource.classification

                        color:
                            root.dataSource.classification === "Normal"
                            ? root.theme.green
                            : root.theme.amber

                        font.pixelSize: 35
                        font.weight: Font.Bold
                    }

                    Text {
                        text:
                            "Model confidence "
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
                        height: 8
                        radius: 4

                        color:
                            root.theme.dark
                            ? "#263248"
                            : "#E6ECF4"

                        Rectangle {
                            width:
                                parent.width
                                * root.dataSource.modelScore

                            height: parent.height
                            radius: 4

                            color:
                                root.dataSource.classification === "Normal"
                                ? root.theme.green
                                : root.theme.amber
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }

                    Text {
                        text:
                            root.dataSource.eventType
                            + " • Session #"
                            + root.dataSource.sessionId
                            + " • "
                            + root.dataSource.eventTime

                        color: root.theme.text2
                        font.pixelSize: 11
                    }
                }
            }

            MetricTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                theme: root.theme
                label: "Heart rate"

                value:
                    root.dataSource.vitalsValid
                    ? root.dataSource.heartRate.toString()
                    : "N/A"

                unit:
                    root.dataSource.vitalsValid
                    ? "BPM"
                    : ""

                note:
                    root.dataSource.vitalsValid
                    ? "Valid measurement"
                    : "Vitals unavailable"

                accentColor: root.theme.red
                trendData: root.dataSource.hrHistory
            }

            MetricTile {
                Layout.fillWidth: true
                Layout.fillHeight: true
                theme: root.theme
                label: "SpO₂"

                value:
                    root.dataSource.vitalsValid
                    ? root.dataSource.spo2.toString()
                    : "N/A"

                unit:
                    root.dataSource.vitalsValid
                    ? "%"
                    : ""

                note:
                    root.dataSource.vitalsValid
                    ? "Valid measurement"
                    : "Vitals unavailable"

                accentColor: root.theme.green
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 3
            columnSpacing: 14
            rowSpacing: 14

            MetricTile {
                Layout.fillWidth: true
                theme: root.theme
                label: "Audio quality"
                value: root.dataSource.audioQuality
                note: "Capture quality"
                accentColor: root.theme.cyan
            }

            MetricTile {
                Layout.fillWidth: true
                theme: root.theme
                label: "Node battery"
                value: root.dataSource.batteryNode.toString()
                unit: "%"
                note: "Patient node"
                accentColor: root.theme.green
            }

            MetricTile {
                Layout.fillWidth: true
                theme: root.theme
                label: "Event type"
                value: root.dataSource.eventType
                note: "Current latest event"
                accentColor: root.theme.purple
            }
        }
    }
}
