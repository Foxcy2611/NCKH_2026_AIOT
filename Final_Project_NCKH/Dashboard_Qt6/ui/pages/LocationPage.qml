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
            title: "Location"
            subtitle: "Gateway position from NEO-M8N GPS"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 480
            spacing: 14

            SurfaceCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 1.7
                theme: root.theme
                accentColor: root.theme.blue

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 18
                    radius: 14
                    color: root.theme.surface2

                    Canvas {
                        anchors.fill: parent

                        onPaint: {
                            var ctx = getContext("2d")

                            ctx.clearRect(
                                0,
                                0,
                                width,
                                height
                            )

                            ctx.strokeStyle =
                                root.theme.dark
                                ? "#22324D"
                                : "#DCE6F2"

                            ctx.lineWidth = 1

                            for (
                                var x = 30;
                                x < width;
                                x += 55
                            ) {
                                ctx.beginPath()
                                ctx.moveTo(x, 0)
                                ctx.lineTo(x, height)
                                ctx.stroke()
                            }

                            for (
                                var y = 30;
                                y < height;
                                y += 55
                            ) {
                                ctx.beginPath()
                                ctx.moveTo(0, y)
                                ctx.lineTo(width, y)
                                ctx.stroke()
                            }
                        }
                    }

                    Rectangle {
                        width: 46
                        height: 46
                        radius: 23
                        color: root.theme.blue
                        anchors.centerIn: parent

                        Rectangle {
                            width: 14
                            height: 14
                            radius: 7
                            color: "white"
                            anchors.centerIn: parent
                        }
                    }

                    Text {
                        text: "Map preview placeholder"
                        color: root.theme.text3
                        font.pixelSize: 11

                        anchors.horizontalCenter:
                            parent.horizontalCenter

                        anchors.bottom:
                            parent.bottom

                        anchors.bottomMargin: 18
                    }
                }
            }

            SurfaceCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 1
                theme: root.theme
                accentColor: root.theme.purple

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 18

                    Text {
                        text: "GPS STATUS"
                        color: root.theme.text3
                        font.pixelSize: 9
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.2
                    }

                    Pill {
                        theme: root.theme

                        label:
                            root.dataSource.gpsValid
                            ? "GPS Fix valid"
                            : "No GPS fix"

                        dotColor:
                            root.dataSource.gpsValid
                            ? root.theme.green
                            : root.theme.red

                        pillColor:
                            root.dataSource.gpsValid
                            ? root.theme.greenSoft
                            : root.theme.redSoft
                    }

                    Column {
                        spacing: 4

                        Text {
                            text: "Latitude"
                            color: root.theme.text3
                            font.pixelSize: 9
                        }

                        Text {
                            text: root.dataSource.latitude.toFixed(6)
                            color: root.theme.text
                            font.pixelSize: 19
                            font.weight: Font.DemiBold
                        }
                    }

                    Column {
                        spacing: 4

                        Text {
                            text: "Longitude"
                            color: root.theme.text3
                            font.pixelSize: 9
                        }

                        Text {
                            text: root.dataSource.longitude.toFixed(6)
                            color: root.theme.text
                            font.pixelSize: 19
                            font.weight: Font.DemiBold
                        }
                    }

                    Column {
                        spacing: 4

                        Text {
                            text: "Last GPS update"
                            color: root.theme.text3
                            font.pixelSize: 9
                        }

                        Text {
                            text: root.dataSource.gpsTime
                            color: root.theme.text
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }

                    Text {
                        Layout.fillWidth: true

                        text:
                            root.dataSource.operatingMode === "MOBILE"
                            ? "Mobile mode: GPS updates continuously/periodically."
                            : "Home mode: cached position can be reused."

                        color: root.theme.text2
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }
}
