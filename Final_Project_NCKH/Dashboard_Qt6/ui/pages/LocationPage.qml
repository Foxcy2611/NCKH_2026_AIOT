import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtLocation
import QtPositioning

import "../components"

Flickable {
    id: root

    required property var theme
    required property var dataSource

    readonly property bool hasLocation: Boolean(dataSource.hasMapLocation)
    readonly property var fallbackCoordinate: QtPositioning.coordinate(16.047079, 108.206230)
    readonly property var gatewayCoordinate: hasLocation
                                                     ? QtPositioning.coordinate(
                                                           Number(dataSource.latitude),
                                                           Number(dataSource.longitude))
                                                     : fallbackCoordinate

    function recenterMap() {
        mapView.map.center = gatewayCoordinate
        mapView.map.zoomLevel = hasLocation ? 16 : 5
    }

    contentWidth: width
    contentHeight: contentColumn.implicitHeight + 52
    clip: true

    ScrollBar.vertical: ScrollBar {}

    Plugin {
        id: osmPlugin
        name: "osm"

        PluginParameter {
            name: "osm.useragent"
            value: "NCKH-AIoT-Respiratory-Monitoring-Dashboard/1.0"
        }
    }

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

                    MapView {
                        id: mapView

                        anchors.fill: parent
                        map.plugin: osmPlugin
                        map.center: root.gatewayCoordinate
                        map.zoomLevel: root.hasLocation ? 16 : 5
                        map.copyrightsVisible: true

                        MapQuickItem {
                            parent: mapView.map
                            visible: root.hasLocation
                            coordinate: root.gatewayCoordinate
                            anchorPoint.x: marker.width / 2
                            anchorPoint.y: marker.height

                            sourceItem: Item {
                                id: marker
                                width: 38
                                height: 46

                                Rectangle {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    y: 4
                                    width: 32
                                    height: 32
                                    radius: 16
                                    color: root.theme.blue
                                    border.color: "white"
                                    border.width: 3

                                    Text {
                                        anchors.centerIn: parent
                                        text: "G"
                                        color: "white"
                                        font.pixelSize: 13
                                        font.bold: true
                                    }
                                }

                                Rectangle {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    y: 35
                                    width: 4
                                    height: 9
                                    radius: 2
                                    color: root.theme.blue
                                }
                            }
                        }
                    }

                    BusyIndicator {
                        anchors.centerIn: parent
                        running: root.hasLocation
                                 && !mapView.map.mapReady
                                 && mapView.map.error === Map.NoError
                        visible: running
                        z: 4
                    }

                    Rectangle {
                        anchors.centerIn: parent
                        width: Math.min(parent.width - 48, 410)
                        height: mapMessage.implicitHeight + 34
                        radius: 12
                        color: root.theme.surface
                        border.color: root.theme.line
                        visible: !root.hasLocation || mapView.map.error !== Map.NoError
                        z: 4

                        Text {
                            id: mapMessage
                            anchors.centerIn: parent
                            width: parent.width - 30
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            color: root.theme.text2
                            font.pixelSize: 12
                            text: !root.hasLocation
                                  ? "Chưa có tọa độ GPS hợp lệ"
                                  : "Không tải được OpenStreetMap. Kiểm tra Internet và module Qt Location.\n"
                                    + mapView.map.errorString
                        }
                    }

                    Column {
                        anchors.top: parent.top
                        anchors.right: parent.right
                        anchors.margins: 12
                        spacing: 6
                        z: 5

                        Repeater {
                            model: [
                                { "label": "+", "hint": "Phóng to", "action": "zoomIn" },
                                { "label": "−", "hint": "Thu nhỏ", "action": "zoomOut" },
                                { "label": "◎", "hint": "Về vị trí Gateway", "action": "recenter" }
                            ]

                            delegate: Button {
                                required property var modelData

                                width: 38
                                height: 38
                                text: modelData.label
                                enabled: mapView.map.mapReady
                                font.pixelSize: modelData.action === "recenter" ? 17 : 20

                                background: Rectangle {
                                    radius: 10
                                    color: parent.hovered
                                           ? root.theme.surface2
                                           : root.theme.surface
                                    border.color: root.theme.line
                                    opacity: 0.94
                                }

                                contentItem: Text {
                                    text: parent.text
                                    color: root.theme.text
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    font: parent.font
                                }

                                onClicked: {
                                    if (modelData.action === "zoomIn") {
                                        mapView.map.zoomLevel = Math.min(
                                                    mapView.maximumZoomLevel,
                                                    mapView.map.zoomLevel + 1)
                                    } else if (modelData.action === "zoomOut") {
                                        mapView.map.zoomLevel = Math.max(
                                                    mapView.minimumZoomLevel,
                                                    mapView.map.zoomLevel - 1)
                                    } else {
                                        root.recenterMap()
                                    }
                                }

                                ToolTip.visible: hovered
                                ToolTip.text: modelData.hint
                            }
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
                        visible: root.hasLocation
                        z: 5

                        Text {
                            id: coordinateText
                            anchors.centerIn: parent
                            text: Number(root.dataSource.latitude).toFixed(6)
                                  + ", "
                                  + Number(root.dataSource.longitude).toFixed(6)
                            color: root.theme.text
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                        }
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
                        label: root.dataSource.gpsValid ? "GPS Fix valid" : "No GPS fix"
                        dotColor: root.dataSource.gpsValid ? root.theme.green : root.theme.red
                        pillColor: root.dataSource.gpsValid
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
                            text: Number(root.dataSource.latitude).toFixed(6)
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
                            text: Number(root.dataSource.longitude).toFixed(6)
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
                        text: root.dataSource.operatingMode === "MOBILE"
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
