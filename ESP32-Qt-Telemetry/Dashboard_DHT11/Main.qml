import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Window {
    width: 600
    height: 400
    visible: true
    title: qsTr("Dashboard NCKH - DHT11")
    color: "#F5F5F5"

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 30

        Text {
            text: "GIÁM SÁT MÔI TRƯỜNG"
            font.pixelSize: 28
            font.bold: true
            color: "#333333"
            Layout.alignment: Qt.AlignHCenter
        }

        RowLayout {
            spacing: 60
            Layout.alignment: Qt.AlignHCenter

            ColumnLayout {
                spacing: 10
                Text { text: "Nhiệt độ"; font.pixelSize: 20; Layout.alignment: Qt.AlignHCenter }
                Text {
                    text: mqttHandler.temperature + " °C"
                    font.pixelSize: 48
                    font.bold: true
                    color: "#D32F2F"
                    Layout.alignment: Qt.AlignHCenter
                }
            }

            ColumnLayout {
                spacing: 10
                Text { text: "Độ ẩm"; font.pixelSize: 20; Layout.alignment: Qt.AlignHCenter }
                Text {
                    text: mqttHandler.humidity + " %"
                    font.pixelSize: 48
                    font.bold: true
                    color: "#1976D2"
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        Button {
            text: "Kết nối HiveMQ Cloud"
            font.pixelSize: 16
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 20
            onClicked: {
                mqttHandler.connectToBroker()
            }
        }
    }
}