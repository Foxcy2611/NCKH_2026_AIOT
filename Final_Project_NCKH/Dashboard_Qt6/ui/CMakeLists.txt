qt_add_executable(
    appDashboard_Qt6
    ../app/main.cpp
)

qt_add_qml_module(
    appDashboard_Qt6

    URI Dashboard_Qt6
    VERSION 1.0

    QML_FILES
        Main.qml
        Theme.qml

        components/Pill.qml
        components/SectionTitle.qml
        components/SurfaceCard.qml
        components/Sparkline.qml
        components/MetricTile.qml
        components/StatusLine.qml
        components/SensorChip.qml
        components/NavItem.qml
        components/Sidebar.qml
        components/TopBar.qml

        pages/OverviewPage.qml
        pages/PatientPage.qml
        pages/EnvironmentPage.qml
        pages/GatewayNetworkPage.qml
        pages/LocationPage.qml

    RESOURCES
        assets/ptit_logo.png
)

target_link_libraries(
    appDashboard_Qt6
    PRIVATE
        Qt6::Qml
        Qt6::Quick
        Qt6::QuickControls2
)

set_target_properties(
    appDashboard_Qt6
    PROPERTIES
        WIN32_EXECUTABLE TRUE
)
