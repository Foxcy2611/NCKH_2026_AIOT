import QtQuick
import QtQuick.Window
import QtQuick.Controls

Window {
    width: 400
    height: 300
    visible: true
    title: qsTr("Dashboard DHT11 - NgocChien Trùm VT01")
    color: "#2c3e50" // Màu nền tối cho ngầu

    // Khai báo một biến để lưu nhiệt độ giả lập
    property int currentTemp: 25

    Column {
        anchors.centerIn: parent
        spacing: 20

        Text {
            text: "Nhiệt độ hiện tại:"
            color: "white"
            font.pixelSize: 20
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Text {
            id: tempDisplay
            text: currentTemp + " °C"
            color: "#e74c3c" // Màu đỏ nổi bật
            font.pixelSize: 60
            font.bold: true
            anchors.horizontalCenter: parent.horizontalCenter

            // Thêm chút animation khi nhiệt độ thay đổi cho mượt
            Behavior on text {
                NumberAnimation { duration: 300 }
            }
        }

        Button {
            text: "Cập nhật dữ liệu"
            font.pixelSize: 16
            anchors.horizontalCenter: parent.horizontalCenter

            // Sự kiện khi bấm nút: Random nhiệt độ từ 20 đến 35
            onClicked: {
                currentTemp = Math.floor(Math.random() * 16) + 20
            }
        }
    }
}