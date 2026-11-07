import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../components"

Flickable {
    id: root

    required property var theme
    required property var dataSource
    required property var profile

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
            title: "Patient profile"
            subtitle: "Identity, respiratory-care context and the latest device snapshot"
        }

        SurfaceCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 205
            theme: root.theme
            accentColor: root.theme.purple

            Rectangle {
                anchors.fill: parent
                anchors.margins: 1
                radius: 17
                color: "transparent"

                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop {
                        position: 0.0
                        color: root.theme.purpleSoft
                    }
                    GradientStop {
                        position: 0.55
                        color: root.theme.surface
                    }
                    GradientStop {
                        position: 1.0
                        color: root.theme.blueSoft
                    }
                }
            }

            RowLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 22

                Rectangle {
                    width: 86
                    height: 86
                    radius: 27
                    color: root.theme.purple

                    Text {
                        anchors.centerIn: parent
                        text: String(root.profile.name || "P").charAt(0).toUpperCase()
                        color: "white"
                        font.pixelSize: 35
                        font.weight: Font.Bold
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.maximumWidth: 390
                    spacing: 7

                    Text {
                        Layout.fillWidth: true
                        text: root.profile.name
                        color: root.theme.text
                        font.pixelSize: 25
                        font.weight: Font.Bold
                        elide: Text.ElideRight
                    }

                    Text {
                        text: root.profile.patientId + "  •  " + root.profile.age + " years  •  " + root.profile.sex
                        color: root.theme.text2
                        font.pixelSize: 12
                    }

                    RowLayout {
                        spacing: 8

                        Pill {
                            theme: root.theme
                            label: root.profile.diagnosis
                            dotColor: root.theme.amber
                            pillColor: root.theme.amberSoft
                        }

                        Pill {
                            theme: root.theme
                            label: "Blood " + root.profile.bloodGroup
                            dotColor: root.theme.red
                            pillColor: root.theme.redSoft
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.profile.careNote
                        color: root.theme.text2
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                }

                Rectangle {
                    Layout.fillHeight: true
                    width: 1
                    color: root.theme.border
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 3
                    columnSpacing: 12
                    rowSpacing: 8

                    Repeater {
                        model: [
                            {
                                "label": "LAST HEART RATE",
                                "value": root.dataSource.heartRateAvailable ? root.dataSource.heartRate + " BPM" : "N/A",
                                "color": root.theme.red
                            },
                            {
                                "label": "LAST SPO₂",
                                "value": root.dataSource.spo2Available ? root.dataSource.spo2 + "%" : "N/A",
                                "color": root.theme.green
                            },
                            {
                                "label": "LATEST RESULT",
                                "value": root.dataSource.classification,
                                "color": root.dataSource.classification === "Non-asthma" ? root.theme.green : root.theme.amber
                            }
                        ]

                        delegate: Rectangle {
                            required property var modelData

                            Layout.fillWidth: true
                            Layout.preferredHeight: 88
                            radius: 14
                            color: root.theme.surface
                            border.width: 1
                            border.color: root.theme.border

                            Column {
                                anchors.fill: parent
                                anchors.margins: 13
                                spacing: 7

                                Rectangle {
                                    width: 9
                                    height: 9
                                    radius: 5
                                    color: modelData.color
                                }

                                Text {
                                    width: parent.width
                                    text: modelData.value
                                    color: root.theme.text
                                    font.pixelSize: 15
                                    font.weight: Font.Bold
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: modelData.label
                                    color: root.theme.text3
                                    font.pixelSize: 8
                                    font.letterSpacing: 0.7
                                }
                            }
                        }
                    }

                    Text {
                        Layout.columnSpan: 3
                        Layout.fillWidth: true
                        text: "Latest event: " + root.dataSource.eventTime + "  •  Session #" + root.dataSource.sessionId
                        color: root.theme.text3
                        font.pixelSize: 10
                        horizontalAlignment: Text.AlignRight
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 335
            spacing: 14

            SurfaceCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                theme: root.theme
                accentColor: root.theme.blue

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 4

                    Text {
                        text: "PERSONAL INFORMATION"
                        color: root.theme.text3
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                        Layout.bottomMargin: 7
                    }

                    InfoRow { Layout.fillWidth: true; theme: root.theme; label: "Date of birth"; value: root.profile.dateOfBirth }
                    InfoRow { Layout.fillWidth: true; theme: root.theme; label: "Sex"; value: root.profile.sex }
                    InfoRow { Layout.fillWidth: true; theme: root.theme; label: "Phone"; value: root.profile.phone }
                    InfoRow { Layout.fillWidth: true; theme: root.theme; label: "Address"; value: root.profile.address }
                    InfoRow { Layout.fillWidth: true; theme: root.theme; label: "Patient ID"; value: root.profile.patientId; showDivider: false }

                    Item { Layout.fillHeight: true }
                }
            }

            SurfaceCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                theme: root.theme
                accentColor: root.theme.amber

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 4

                    Text {
                        text: "RESPIRATORY CARE"
                        color: root.theme.text3
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                        Layout.bottomMargin: 7
                    }

                    InfoRow { Layout.fillWidth: true; theme: root.theme; label: "Diagnosis"; value: root.profile.diagnosis; valueColor: root.theme.amber }
                    InfoRow { Layout.fillWidth: true; theme: root.theme; label: "Severity"; value: root.profile.severity }
                    InfoRow { Layout.fillWidth: true; theme: root.theme; label: "Common triggers"; value: root.profile.triggers }
                    InfoRow { Layout.fillWidth: true; theme: root.theme; label: "Allergies"; value: root.profile.allergies }
                    InfoRow { Layout.fillWidth: true; theme: root.theme; label: "Medication"; value: root.profile.medication; showDivider: false }

                    Item { Layout.fillHeight: true }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 205
            spacing: 14

            SurfaceCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                theme: root.theme
                accentColor: root.theme.red

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 8

                    Text {
                        text: "EMERGENCY CONTACT"
                        color: root.theme.text3
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                    }

                    Text {
                        text: root.profile.emergencyName
                        color: root.theme.text
                        font.pixelSize: 20
                        font.weight: Font.Bold
                    }

                    Text {
                        text: root.profile.emergencyRelation + "  •  " + root.profile.emergencyPhone
                        color: root.theme.text2
                        font.pixelSize: 12
                    }

                    Item { Layout.fillHeight: true }

                    Pill {
                        theme: root.theme
                        label: "Primary emergency contact"
                        dotColor: root.theme.red
                        pillColor: root.theme.redSoft
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
                    spacing: 12

                    Text {
                        text: "DEVICE CONTEXT"
                        color: root.theme.text3
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "Patient node"
                        value: root.dataSource.batteryNodeAvailable ? root.dataSource.batteryNode + "% battery" : "Battery N/A"
                        good: root.dataSource.batteryNodeAvailable && root.dataSource.batteryNode > 20
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "Audio quality"
                        value: root.dataSource.audioQuality
                        good: root.dataSource.audioQuality === "GOOD"
                    }

                    StatusLine {
                        Layout.fillWidth: true
                        theme: root.theme
                        label: "Cloud link"
                        value: root.dataSource.mqttConnected ? "Online" : "Offline"
                        good: root.dataSource.mqttConnected
                    }
                }
            }
        }
    }
}
