import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "components"
import "pages"

ApplicationWindow {
    id: root

    width: 1440
    height: 900

    minimumWidth: 1160
    minimumHeight: 720

    visible: true

    title: "Respiratory Monitoring Dashboard"

    Theme {
        id: appTheme
    }

    color: appTheme.page

    // ============================================================
    // PATIENT DEMO INFO
    // ============================================================

    property string patientName:
        "Nguyễn Văn A"

    property string patientId:
        "Patient #001"


    // ============================================================
    // INLINE FRONTEND MOCK DATA
    //
    // Sau này có backend thì thay dataSource hoặc bind QObject C++.
    // ============================================================

    QtObject {
        id: demo

        // Gateway
        property int gatewayId: 1
        property string operatingMode: "HOME"
        property string uplinkType: "Wi-Fi"
        property int batteryGate: 84

        // Environment
        property real temperature: 28.4
        property real humidity: 67.2
        property real pressure: 1008.6
        property int tvoc: 118
        property int eco2: 532

        // Sensor health
        property bool dhtValid: true
        property bool bmpValid: true
        property bool sgpValid: true
        property bool gpsValid: true

        // Network
        property bool wifiConnected: true
        property int wifiRssi: -55
        property bool lteRegistered: true
        property int lteRssi: -87
        property bool mqttConnected: true

        // GPS
        property real latitude: 21.028511
        property real longitude: 105.804817
        property string gpsTime: "23:18:42"

        // Patient
        property bool hasPatientEvent: true
        property int sessionId: 25
        property string eventTime: "23:17:58"
        property string eventType: "Manual Check"
        property string classification: "Asthma-like"
        property real modelScore: 0.932
        property string audioQuality: "GOOD"
        property bool vitalsValid: true
        property int heartRate: 82
        property int spo2: 97
        property int batteryNode: 76

        // Fake history
        property var tempHistory:
            [27.7, 27.9, 28.0, 28.4, 28.2, 28.6, 28.4, 28.8, 28.5, 28.4]

        property var humHistory:
            [64, 65, 64, 66, 67, 67, 68, 66, 67, 67.2]

        property var hrHistory:
            [76, 79, 81, 78, 82, 84, 80, 83, 81, 82]


        function rand(minimum, maximum) {
            return minimum
                    + Math.random()
                    * (maximum - minimum)
        }


        function randInt(minimum, maximum) {
            return Math.floor(
                rand(
                    minimum,
                    maximum + 1
                )
            )
        }


        function pushHistory(array, value) {
            var copy = array.slice(0)

            copy.push(value)

            if (copy.length > 14)
                copy.shift()

            return copy
        }


        function tick() {
            temperature = rand(26.7, 30.5)
            humidity = rand(57.0, 78.0)
            pressure = rand(1003.0, 1013.0)

            tvoc = randInt(80, 220)
            eco2 = randInt(430, 780)

            wifiRssi = randInt(-69, -43)
            lteRssi = randInt(-99, -74)

            tempHistory =
                pushHistory(
                    tempHistory,
                    temperature
                )

            humHistory =
                pushHistory(
                    humHistory,
                    humidity
                )

            // Patient data chỉ update khi có event mới.
            hasPatientEvent =
                Math.random() < 0.25

            if (hasPatientEvent) {
                sessionId += 1

                heartRate =
                    randInt(66, 102)

                spo2 =
                    randInt(94, 100)

                modelScore =
                    rand(0.75, 0.98)

                classification =
                    Math.random() > 0.55
                    ? "Normal"
                    : "Asthma-like"

                eventType =
                    Math.random() > 0.5
                    ? "Manual Check"
                    : "Monitor Event"

                audioQuality =
                    Math.random() > 0.15
                    ? "GOOD"
                    : "LOW"

                batteryNode =
                    Math.max(
                        1,
                        batteryNode
                        - (
                            Math.random() > 0.82
                            ? 1
                            : 0
                        )
                    )

                hrHistory =
                    pushHistory(
                        hrHistory,
                        heartRate
                    )
            }

            batteryGate =
                Math.max(
                    1,
                    batteryGate
                    - (
                        Math.random() > 0.94
                        ? 1
                        : 0
                    )
                )
        }
    }


    property var dataSource:
        demo


    Timer {
        interval: 2200
        running: true
        repeat: true

        onTriggered:
            demo.tick()
    }


    // ============================================================
    // NAVIGATION
    // ============================================================

    property int currentPage: 0


    Component {
        id: overviewPageComponent

        OverviewPage {
            theme: appTheme
            dataSource: root.dataSource
        }
    }


    Component {
        id: patientPageComponent

        PatientPage {
            theme: appTheme
            dataSource: root.dataSource
        }
    }


    Component {
        id: environmentPageComponent

        EnvironmentPage {
            theme: appTheme
            dataSource: root.dataSource
        }
    }


    Component {
        id: gatewayNetworkPageComponent

        GatewayNetworkPage {
            theme: appTheme
            dataSource: root.dataSource
        }
    }


    Component {
        id: locationPageComponent

        LocationPage {
            theme: appTheme
            dataSource: root.dataSource
        }
    }


    function pageComponent(index) {
        switch (index) {
        case 0: return overviewPageComponent
        case 1: return patientPageComponent
        case 2: return environmentPageComponent
        case 3: return gatewayNetworkPageComponent
        case 4: return locationPageComponent
        default: return overviewPageComponent
        }
    }


    function navigateTo(index) {
        if (root.currentPage === index)
            return

        root.currentPage = index

        pageStack.replace(
            pageComponent(index)
        )
    }


    // ============================================================
    // APP LAYOUT
    // ============================================================

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Sidebar {
            Layout.preferredWidth: 258
            Layout.fillHeight: true

            theme: appTheme
            dataSource: root.dataSource
            currentPage: root.currentPage

            patientName: root.patientName
            patientId: root.patientId

            ptitLogoSource:
                Qt.resolvedUrl(
                    "assets/ptit_logo.png"
                )

            onPageRequested:
                function(pageIndex) {
                    root.navigateTo(pageIndex)
                }
        }


        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            TopBar {
                Layout.fillWidth: true
                Layout.preferredHeight: 72

                theme: appTheme
                dataSource: root.dataSource
                currentPage: root.currentPage

                onThemeToggle:
                    appTheme.dark =
                        !appTheme.dark
            }


            StackView {
                id: pageStack

                Layout.fillWidth: true
                Layout.fillHeight: true

                clip: true

                initialItem:
                    overviewPageComponent

                replaceEnter:
                    Transition {
                        ParallelAnimation {
                            NumberAnimation {
                                property: "opacity"
                                from: 0
                                to: 1
                                duration: 160
                            }

                            NumberAnimation {
                                property: "x"
                                from: 14
                                to: 0
                                duration: 160
                            }
                        }
                    }

                replaceExit:
                    Transition {
                        NumberAnimation {
                            property: "opacity"
                            from: 1
                            to: 0
                            duration: 90
                        }
                    }
            }
        }
    }
}
