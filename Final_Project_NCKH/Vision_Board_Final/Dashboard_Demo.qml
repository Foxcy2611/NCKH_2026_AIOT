import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

// FILE Này demo giao diện dashboard

Window {
    id: root
    width: 1280
    height: 800
    visible: true
    title: "Health Monitoring Dashboard - ESP32 & MQTT"

    property bool isDarkMode: false

    color: bgApp

    // ============ DYNAMIC PALETTE (SÁNG/TỐI) ============
    readonly property color bgApp: isDarkMode ? "#0D1117" : "#F4F6F8"
    readonly property color cardBg: isDarkMode ? "#161B22" : "#FFFFFF"
    readonly property color cardBorder: isDarkMode ? "#21262D" : "#E2E8F0"

    readonly property color textPrimary: isDarkMode ? "#E6EDF3" : "#1E293B"
    readonly property color textSecondary: isDarkMode ? "#8B949E" : "#64748B"

    readonly property color accentBlue: isDarkMode ? "#58A6FF" : "#3B82F6"
    readonly property color accentGreen: isDarkMode ? "#3FB950" : "#10B981"
    readonly property color accentRed: isDarkMode ? "#F85149" : "#EF4444"
    readonly property color accentYellow: isDarkMode ? "#D29922" : "#F59E0B"
    readonly property color accentPurple: isDarkMode ? "#BC8CFF" : "#8B5CF6"

    // Các màu phụ trợ cho thanh tiến trình và cảnh báo
    readonly property color trackBg: isDarkMode ? "#21262D" : "#E2E8F0"
    readonly property color mqttBg: isDarkMode ? "#1A7F37" : "#D1FAE5"
    readonly property color mqttText: isDarkMode ? "#F0FFF4" : "#047857"
    readonly property color safeBg: isDarkMode ? "#122B1B" : "#D1FAE5"
    readonly property color warnBg: isDarkMode ? "#3B1414" : "#FEE2E2"
    readonly property color sosBg: isDarkMode ? "#2D1114" : "#FEF2F2"
    readonly property color btnDisabled: isDarkMode ? "#30363D" : "#CBD5E1"

    // ============ FIXED SAMPLE DATA ============
    property string patientName: "Nguyễn Ngọc Chiến"
    property int patientAge: 20
    property string patientGender: "Nam"
    property string bloodType: "O+"
    property string patientHistory: "Tăng huyết áp, Hen suyễn"
    property string patientId: "PT-2026-0091"

    property int heartRate: 78
    property int spo2: 97
    property double bodyTemp: 36.8

    property double roomTemp: 26.4
    property double roomHumidity: 58
    property double pressure: 1012.6

    property int eco2: 620
    property int tvoc: 145

    property double gpsLat: 21.301400
    property double gpsLng: 105.402100
    property bool inSafeZone: true

    property bool sosActive: false
    property string lastAlert: "Không có cảnh báo mới"

    Behavior on color {
        ColorAnimation {
            duration: 300
        }
    }

    // ============ HEADER ============
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 20

        RowLayout {
            Layout.fillWidth: true
            spacing: 16

            Rectangle {
                width: 46
                height: 46
                radius: 12
                color: accentBlue

                Text {
                    anchors.centerIn: parent
                    text: "🏥"
                    font.pixelSize: 22
                }
            }

            ColumnLayout {
                spacing: 2

                Text {
                    text: "Health Monitoring Dashboard"
                    color: textPrimary
                    font.pixelSize: 22
                    font.bold: true
                }

                Text {
                    text: "ESP32 · MQTT · Real-time Vitals & Environment"
                    color: textSecondary
                    font.pixelSize: 13
                }
            }

            Item {
                Layout.fillWidth: true
            }

            // Nút Chuyển đổi Theme Sáng/Tối
            Rectangle {
                width: 46
                height: 46
                radius: 12
                color: cardBg
                border.color: cardBorder
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: isDarkMode ? "🌙" : "☀️"
                    font.pixelSize: 20
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: isDarkMode = !isDarkMode
                }

                Behavior on color {
                    ColorAnimation {
                        duration: 300
                    }
                }
            }

            Rectangle {
                width: 130
                height: 34
                radius: 17
                color: mqttBg
                border.color: accentGreen
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 6

                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: accentGreen

                        SequentialAnimation on opacity {
                            loops: Animation.Infinite
                            NumberAnimation {
                                from: 1
                                to: 0.3
                                duration: 800
                            }
                            NumberAnimation {
                                from: 0.3
                                to: 1
                                duration: 800
                            }
                        }
                    }

                    Text {
                        text: "MQTT Connected"
                        color: mqttText
                        font.pixelSize: 12
                        font.bold: true
                    }
                }

                Behavior on color {
                    ColorAnimation {
                        duration: 300
                    }
                }
            }
        }

        // ============ MAIN GRID ============
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            // --- LEFT COLUMN: Patient + GPS + Alerts ---
            ColumnLayout {
                Layout.preferredWidth: 320
                Layout.fillHeight: true
                spacing: 20

                // Patient Card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 260
                    radius: 16
                    color: cardBg
                    border.color: cardBorder
                    border.width: 1

                    Behavior on color {
                        ColorAnimation {
                            duration: 300
                        }
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 12

                        RowLayout {
                            spacing: 12

                            Rectangle {
                                width: 56
                                height: 56
                                radius: 28
                                color: trackBg

                                Text {
                                    anchors.centerIn: parent
                                    text: "👤"
                                    font.pixelSize: 26
                                }
                            }

                            ColumnLayout {
                                spacing: 2

                                Text {
                                    text: patientName
                                    color: textPrimary
                                    font.pixelSize: 17
                                    font.bold: true
                                }

                                Text {
                                    text: patientId
                                    color: accentBlue
                                    font.pixelSize: 12
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: cardBorder
                        }

                        GridLayout {
                            columns: 2
                            columnSpacing: 16
                            rowSpacing: 10
                            Layout.fillWidth: true

                            Text {
                                text: "Tuổi"
                                color: textSecondary
                                font.pixelSize: 12
                            }

                            Text {
                                text: patientAge + " tuổi"
                                color: textPrimary
                                font.pixelSize: 13
                                Layout.alignment: Qt.AlignRight
                            }

                            Text {
                                text: "Giới tính"
                                color: textSecondary
                                font.pixelSize: 12
                            }

                            Text {
                                text: patientGender
                                color: textPrimary
                                font.pixelSize: 13
                                Layout.alignment: Qt.AlignRight
                            }

                            Text {
                                text: "Nhóm máu"
                                color: textSecondary
                                font.pixelSize: 12
                            }

                            Text {
                                text: bloodType
                                color: accentRed
                                font.pixelSize: 13
                                font.bold: true
                                Layout.alignment: Qt.AlignRight
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: cardBorder
                        }

                        Text {
                            text: "Tiền sử bệnh lý"
                            color: textSecondary
                            font.pixelSize: 12
                        }

                        Text {
                            text: patientHistory
                            color: accentYellow
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                // GPS Card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 160
                    radius: 16
                    color: cardBg
                    border.color: cardBorder
                    border.width: 1

                    Behavior on color {
                        ColorAnimation {
                            duration: 300
                        }
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 10

                        RowLayout {
                            spacing: 8

                            Text {
                                text: "📍"
                                font.pixelSize: 16
                            }

                            Text {
                                text: "Vị trí (GPS)"
                                color: textPrimary
                                font.pixelSize: 14
                                font.bold: true
                            }

                            Item {
                                Layout.fillWidth: true
                            }

                            Rectangle {
                                width: 90
                                height: 22
                                radius: 11
                                color: inSafeZone ? safeBg : warnBg
                                border.color: inSafeZone ? accentGreen : accentRed
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: inSafeZone ? "An toàn" : "Cảnh báo"
                                    color: inSafeZone ? accentGreen : accentRed
                                    font.pixelSize: 10
                                    font.bold: true
                                }
                            }
                        }

                        Text {
                            text: "Vĩ độ: " + gpsLat.toFixed(6)
                            color: textSecondary
                            font.pixelSize: 12
                        }

                        Text {
                            text: "Kinh độ: " + gpsLng.toFixed(6)
                            color: textSecondary
                            font.pixelSize: 12
                        }
                    }
                }

                // Alert Card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 16
                    color: sosActive ? sosBg : cardBg
                    border.color: sosActive ? accentRed : cardBorder
                    border.width: sosActive ? 2 : 1

                    Behavior on color {
                        ColorAnimation {
                            duration: 300
                        }
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 10

                        RowLayout {
                            spacing: 8

                            Text {
                                text: "🚨"
                                font.pixelSize: 16
                            }

                            Text {
                                text: "Cảnh báo & SOS"
                                color: textPrimary
                                font.pixelSize: 14
                                font.bold: true
                            }
                        }

                        Text {
                            text: lastAlert
                            color: sosActive ? accentRed : textSecondary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Item {
                            Layout.fillHeight: true
                        }

                        Button {
                            Layout.fillWidth: true
                            text: "Gọi khẩn cấp / Gửi SMS"
                            enabled: sosActive

                            background: Rectangle {
                                radius: 10
                                color: parent.enabled ? accentRed : btnDisabled

                                Behavior on color {
                                    ColorAnimation {
                                        duration: 200
                                    }
                                }
                            }

                            contentItem: Text {
                                text: parent.text
                                color: parent.enabled ? "white" : textSecondary
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: 13
                                font.bold: true
                            }
                        }
                    }
                }
            }

            // --- RIGHT COLUMN: Vitals + Environment ---
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 20

                Text {
                    text: "Chỉ số sinh tồn (Vital Signs)"
                    color: textPrimary
                    font.pixelSize: 15
                    font.bold: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 20

                    // Heart Rate
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 150
                        radius: 16
                        color: cardBg
                        border.color: cardBorder
                        border.width: 1

                        Behavior on color {
                            ColorAnimation {
                                duration: 300
                            }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 6

                            RowLayout {
                                spacing: 8

                                Text {
                                    text: "❤️"
                                    font.pixelSize: 18
                                }

                                Text {
                                    text: "Nhịp tim"
                                    color: textSecondary
                                    font.pixelSize: 12
                                }
                            }

                            RowLayout {
                                spacing: 6
                                Layout.alignment: Qt.AlignBottom

                                Text {
                                    text: heartRate
                                    color: accentRed
                                    font.pixelSize: 36
                                    font.bold: true
                                }

                                Text {
                                    text: "bpm"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    Layout.alignment: Qt.AlignBottom
                                    Layout.bottomMargin: 6
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 6
                                radius: 3
                                color: trackBg

                                Rectangle {
                                    width: parent.width * Math.min(heartRate/150, 1)
                                    height: parent.height
                                    radius: 3
                                    color: accentRed
                                }
                            }

                            Text {
                                text: "Ngưỡng bình thường: 60–100 bpm"
                                color: textSecondary
                                font.pixelSize: 10
                            }
                        }
                    }

                    // SpO2
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 150
                        radius: 16
                        color: cardBg
                        border.color: cardBorder
                        border.width: 1

                        Behavior on color {
                            ColorAnimation {
                                duration: 300
                            }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 6

                            RowLayout {
                                spacing: 8

                                Text {
                                    text: "🫁"
                                    font.pixelSize: 18
                                }

                                Text {
                                    text: "SpO2"
                                    color: textSecondary
                                    font.pixelSize: 12
                                }
                            }

                            RowLayout {
                                spacing: 6
                                Layout.alignment: Qt.AlignBottom

                                Text {
                                    text: spo2
                                    color: accentBlue
                                    font.pixelSize: 36
                                    font.bold: true
                                }

                                Text {
                                    text: "%"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    Layout.alignment: Qt.AlignBottom
                                    Layout.bottomMargin: 6
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 6
                                radius: 3
                                color: trackBg

                                Rectangle {
                                    width: parent.width * Math.min(spo2/100, 1)
                                    height: parent.height
                                    radius: 3
                                    color: accentBlue
                                }
                            }

                            Text {
                                text: "Ngưỡng an toàn: ≥ 90%"
                                color: textSecondary
                                font.pixelSize: 10
                            }
                        }
                    }

                    // Body Temp
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 150
                        radius: 16
                        color: cardBg
                        border.color: cardBorder
                        border.width: 1

                        Behavior on color {
                            ColorAnimation {
                                duration: 300
                            }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 6

                            RowLayout {
                                spacing: 8

                                Text {
                                    text: "🌡️"
                                    font.pixelSize: 18
                                }

                                Text {
                                    text: "Thân nhiệt"
                                    color: textSecondary
                                    font.pixelSize: 12
                                }
                            }

                            RowLayout {
                                spacing: 6
                                Layout.alignment: Qt.AlignBottom

                                Text {
                                    text: bodyTemp.toFixed(1)
                                    color: accentGreen
                                    font.pixelSize: 36
                                    font.bold: true
                                }

                                Text {
                                    text: "°C"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    Layout.alignment: Qt.AlignBottom
                                    Layout.bottomMargin: 6
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 6
                                radius: 3
                                color: trackBg

                                Rectangle {
                                    width: parent.width * Math.min(bodyTemp/42, 1)
                                    height: parent.height
                                    radius: 3
                                    color: accentGreen
                                }
                            }

                            Text {
                                text: "Bình thường: 36.1–37.2°C"
                                color: textSecondary
                                font.pixelSize: 10
                            }
                        }
                    }
                }

                Text {
                    text: "Môi trường phòng bệnh (Indoor Environment)"
                    color: textPrimary
                    font.pixelSize: 15
                    font.bold: true
                    Layout.topMargin: 8
                }

                GridLayout {
                    columns: 3
                    rowSpacing: 20
                    columnSpacing: 20
                    Layout.fillWidth: true

                    // DHT11
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        radius: 16
                        color: cardBg
                        border.color: cardBorder
                        border.width: 1

                        Behavior on color {
                            ColorAnimation {
                                duration: 300
                            }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 10

                            RowLayout {
                                spacing: 8

                                Text {
                                    text: "💧"
                                    font.pixelSize: 16
                                }

                                Text {
                                    text: "Điều kiện phòng"
                                    color: textPrimary
                                    font.pixelSize: 13
                                    font.bold: true
                                }
                            }

                            Text {
                                text: "Nhiệt độ phòng"
                                color: textSecondary
                                font.pixelSize: 11
                            }

                            Text {
                                text: roomTemp.toFixed(1) + " °C"
                                color: textPrimary
                                font.pixelSize: 22
                                font.bold: true
                            }

                            Text {
                                text: "Độ ẩm"
                                color: textSecondary
                                font.pixelSize: 11
                            }

                            Text {
                                text: roomHumidity.toFixed(0) + " %"
                                color: accentBlue
                                font.pixelSize: 22
                                font.bold: true
                            }

                            Item {
                                Layout.fillHeight: true
                            }
                        }
                    }

                    // BMP280
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        radius: 16
                        color: cardBg
                        border.color: cardBorder
                        border.width: 1

                        Behavior on color {
                            ColorAnimation {
                                duration: 300
                            }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 10

                            RowLayout {
                                spacing: 8

                                Text {
                                    text: "🧭"
                                    font.pixelSize: 16
                                }

                                Text {
                                    text: "Khí quyển"
                                    color: textPrimary
                                    font.pixelSize: 13
                                    font.bold: true
                                }
                            }

                            Text {
                                text: "Áp suất khí quyển"
                                color: textSecondary
                                font.pixelSize: 11
                            }

                            Text {
                                text: pressure.toFixed(1) + " hPa"
                                color: textPrimary
                                font.pixelSize: 22
                                font.bold: true
                            }

                            Item {
                                Layout.fillHeight: true
                            }

                            Text {
                                text: "Trạng thái: Ổn định"
                                color: accentGreen
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }
                    }

                    // SGP30
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        radius: 16
                        color: cardBg
                        border.color: cardBorder
                        border.width: 1

                        Behavior on color {
                            ColorAnimation {
                                duration: 300
                            }
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 10

                            RowLayout {
                                spacing: 8

                                Text {
                                    text: "🌫️"
                                    font.pixelSize: 16
                                }

                                Text {
                                    text: "SGP30"
                                    color: textPrimary
                                    font.pixelSize: 13
                                    font.bold: true
                                }
                            }

                            Text {
                                text: "eCO2"
                                color: textSecondary
                                font.pixelSize: 11
                            }

                            Text {
                                text: eco2 + " ppm"
                                color: accentYellow
                                font.pixelSize: 20
                                font.bold: true
                            }

                            Text {
                                text: "TVOC"
                                color: textSecondary
                                font.pixelSize: 11
                            }

                            Text {
                                text: tvoc + " ppb"
                                color: accentPurple
                                font.pixelSize: 20
                                font.bold: true
                            }

                            Item {
                                Layout.fillHeight: true
                            }
                        }
                    }

                    // Trạng thái phần cứng (Node Status) lấp đầy khoảng trống thay thế MQ135
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 100
                        Layout.columnSpan: 3
                        radius: 16
                        color: cardBg
                        border.color: cardBorder
                        border.width: 1

                        Behavior on color {
                            ColorAnimation {
                                duration: 300
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 30

                            ColumnLayout {
                                spacing: 6

                                RowLayout {
                                    spacing: 5

                                    Text {
                                        text: "⚙️"
                                        font.pixelSize: 16
                                    }

                                    Text {
                                        text: "Trạng thái phần cứng (Node Status)"
                                        color: textPrimary
                                        font.pixelSize: 13
                                        font.bold: true
                                    }
                                }

                                Text {
                                    text: "Thông số kết nối và pin của thiết bị ESP32"
                                    color: textSecondary
                                    font.pixelSize: 11
                                }
                            }

                            ColumnLayout {
                                spacing: 4

                                Text {
                                    text: "Pin thiết bị"
                                    color: textSecondary
                                    font.pixelSize: 11
                                    Layout.alignment: Qt.AlignHCenter
                                }

                                Text {
                                    text: "🔋 85%"
                                    color: accentGreen
                                    font.pixelSize: 16
                                    font.bold: true
                                    Layout.alignment: Qt.AlignHCenter
                                }
                            }

                            Rectangle {
                                width: 1
                                Layout.fillHeight: true
                                color: cardBorder
                            }

                            ColumnLayout {
                                spacing: 4

                                Text {
                                    text: "Tín hiệu WiFi"
                                    color: textSecondary
                                    font.pixelSize: 11
                                    Layout.alignment: Qt.AlignHCenter
                                }

                                Text {
                                    text: "📶 -62 dBm"
                                    color: accentBlue
                                    font.pixelSize: 16
                                    font.bold: true
                                    Layout.alignment: Qt.AlignHCenter
                                }
                            }

                            Rectangle {
                                width: 1
                                Layout.fillHeight: true
                                color: cardBorder
                            }

                            ColumnLayout {
                                spacing: 4

                                Text {
                                    text: "Đồng bộ lần cuối"
                                    color: textSecondary
                                    font.pixelSize: 11
                                    Layout.alignment: Qt.AlignHCenter
                                }

                                Text {
                                    text: "⏱️ Vừa xong"
                                    color: textPrimary
                                    font.pixelSize: 16
                                    font.bold: true
                                    Layout.alignment: Qt.AlignHCenter
                                }
                            }
                        }
                    }
                }

                Item {
                    Layout.fillHeight: true
                }
            }
        }
    }
}