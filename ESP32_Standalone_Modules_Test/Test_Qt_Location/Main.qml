import QtQuick
import QtQuick.Controls
import QtLocation
import QtPositioning

Window {
    width: 800
    height: 600
    visible: true
    title: "Asthma Tracking Dashboard"

    Plugin {
        id: mapPlugin
        name: "osm"
        // Fix lỗi load map chậm của OpenStreetMap
        PluginParameter { name: "osm.mapping.providersrepository.disabled"; value: "true" }
        PluginParameter { name: "osm.mapping.providersrepository.address"; value: "http://maps-redirect.qt.io/osm/5.6/" }
    }

    Map {
        id: map
        anchors.fill: parent
        plugin: mapPlugin
        center: QtPositioning.coordinate(20.980649, 105.787687)
        zoomLevel: 15

        MapQuickItem {
            coordinate: QtPositioning.coordinate(20.980649, 105.787687)
            anchorPoint.x: sourceItem.width / 2
            anchorPoint.y: sourceItem.height / 2

            sourceItem: Rectangle {
                width: 20
                height: 20
                color: "red"
                radius: 10
                border.color: "white"
                border.width: 2

                SequentialAnimation on opacity {
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 1000 }
                    NumberAnimation { to: 1.0; duration: 1000 }
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onWheel: (wheel) => {
                if (wheel.angleDelta.y > 0) map.zoomLevel += 0.5
                else map.zoomLevel -= 0.5
            }
        }
    }
}