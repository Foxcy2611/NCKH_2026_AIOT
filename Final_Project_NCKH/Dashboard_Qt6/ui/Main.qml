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

    property string patientName: "Nguyễn Văn A"
    property string patientId: "Patient #001"

    // QObject C++ được đăng ký trong main.cpp. QML chỉ hiển thị dữ liệu.
    property var dataSource: dashboardBackend

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
        pageStack.replace(pageComponent(index))
    }

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
            ptitLogoSource: Qt.resolvedUrl("assets/ptit_logo.png")

            onPageRequested: function(pageIndex) {
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

                onThemeToggle: appTheme.dark = !appTheme.dark
            }

            StackView {
                id: pageStack

                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                initialItem: overviewPageComponent

                replaceEnter: Transition {
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

                replaceExit: Transition {
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
