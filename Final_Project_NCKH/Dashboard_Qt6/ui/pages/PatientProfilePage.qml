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

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 318

            radius: 18
            color: root.theme.surface2
            border.width: 1
            border.color: root.theme.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 13

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 80
                    spacing: 15

                    Rectangle {
                        Layout.preferredWidth: 80
                        Layout.preferredHeight: 80
                        radius: 15
                        color: root.theme.purple

                        Text {
                            anchors.centerIn: parent
                            text: root.profile.shortId || "01"
                            color: "white"
                            font.pixelSize: 28
                            font.weight: Font.Bold
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            Layout.fillWidth: true
                            text: root.profile.name
                            color: root.theme.text
                            font.pixelSize: 24
                            font.weight: Font.Bold
                            elide: Text.ElideRight
                        }

                        Text {
                            text: "Subject ID: " + root.profile.patientId
                            color: root.theme.text2
                            font.pixelSize: 13
                        }

                        RowLayout {
                            spacing: 8

                            Pill {
                                theme: root.theme
                                label: root.profile.participantType || root.profile.diagnosis
                                dotColor: root.theme.green
                                pillColor: root.theme.greenSoft
                            }

                            Pill {
                                theme: root.theme
                                label: root.profile.sessionLabel || "Demo session"
                                dotColor: root.theme.blue
                                pillColor: root.theme.blueSoft
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: root.profile.studyNote || root.profile.careNote
                    color: root.theme.text2
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: root.theme.border
                }

                GridLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 76
                    columns: 3
                    columnSpacing: 10

                    Repeater {
                        model: [
                            {
                                "label": "HEART RATE",
                                "value": root.dataSource.heartRateAvailable
                                         ? root.dataSource.heartRate + " BPM"
                                         : "N/A"
                            },
                            {
                                "label": "SpO₂",
                                "value": root.dataSource.spo2Available
                                         ? root.dataSource.spo2 + "%"
                                         : "N/A"
                            },
                            {
                                "label": "AI CLASSIFICATION",
                                "value": root.dataSource.classification
                            }
                        ]

                        delegate: Rectangle {
                            required property var modelData

                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 11
                            color: root.theme.surface
                            border.width: 1
                            border.color: root.theme.border

                            Column {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 7

                                Text {
                                    width: parent.width
                                    text: modelData.value
                                    color: root.theme.text
                                    font.pixelSize: 22
                                    font.weight: Font.Bold
                                    elide: Text.ElideRight
                                }

                                Text {
                                    width: parent.width
                                    text: modelData.label
                                    color: root.theme.text3
                                    font.pixelSize: 9
                                    font.letterSpacing: 0.4
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: {
                        var eventUptime = String(root.dataSource.eventTime || "N/A")
                        if (eventUptime.indexOf("Uptime ") === 0)
                            eventUptime = eventUptime.substring(7)
                        if (eventUptime === "N/A")
                            eventUptime = "--:--:--"
                        return "Session uptime: " + eventUptime + "  •  " + root.profile.patientId
                    }
                    color: root.theme.text2
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignRight
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
