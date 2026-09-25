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
                    id: mapFrame

                    anchors.fill: parent
                    anchors.margins: 18
                    radius: 14
                    color: root.theme.surface2
                    clip: true

                    Image {
                        id: googleMap

                        anchors.fill: parent
                        source: root.dataSource.googleStaticMapUrl
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        retainWhileLoading: true
                        smooth: true
                    }

                    BusyIndicator {
                        anchors.centerIn: parent
                        running: googleMap.status === Image.Loading
                        visible: running
                    }

                    Rectangle {
                        anchors.centerIn: parent
                        width: Math.min(parent.width - 48, 390)
                        height: mapMessage.implicitHeight + 34
                        radius: 12
                        color: root.theme.surface
                        border.color: root.theme.line
                        visible: googleMap.status === Image.Error
                                 || !root.dataSource.hasMapLocation
                                 || !root.dataSource.googleMapsConfigured

                        Text {
                            id: mapMessage
                            anchors.centerIn: parent
                            width: parent.width - 30
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            color: root.theme.text2
                            font.pixelSize: 12
                            text: !root.dataSource.hasMapLocation
                                  ? "Chưa có tọa độ GPS hợp lệ"
                                  : !root.dataSource.googleMapsConfigured
                                    ? "Chưa cấu hình NCKH_GOOGLE_MAPS_API_KEY"
                                    : "Không tải được Google Maps. Kiểm tra Internet và quyền Maps Static API."
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.bottom: parent.bottom
                        anchors.margins: 12
                        width: coordinateText.implicitWidth + 22
                        height: 30
                        radius: 9
                        color: root.theme.surface
                        opacity: 0.92
                        visible: root.dataSource.hasMapLocation

                        Text {
                            id: coordinateText
                            anchors.centerIn: parent
                            text: root.dataSource.latitude.toFixed(6)
                                  + ", "
                                  + root.dataSource.longitude.toFixed(6)
                            color: root.theme.text
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: root.dataSource.hasMapLocation
                        hoverEnabled: true
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: Qt.openUrlExternally(root.dataSource.googleMapsUrl)

                        ToolTip.visible: containsMouse
                        ToolTip.text: "Mở vị trí này trên Google Maps"
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
