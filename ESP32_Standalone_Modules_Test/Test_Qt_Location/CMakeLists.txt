cmake_minimum_required(VERSION 3.16)

project(Test_Qt_Location VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Qml Quick Positioning Location)

qt_standard_project_setup(REQUIRES 6.11)

qt_add_executable(appTest_Qt_Location
    main.cpp
)

qt_add_qml_module(appTest_Qt_Location
    URI Test_Qt_Location
    QML_FILES
        Main.qml
)

# Qt for iOS sets MACOSX_BUNDLE_GUI_IDENTIFIER automatically since Qt 6.1.
# If you are developing for iOS or macOS you should consider setting an
# explicit, fixed bundle identifier manually though.
set_target_properties(appTest_Qt_Location PROPERTIES
#    MACOSX_BUNDLE_GUI_IDENTIFIER com.example.appTest_Qt_Location
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE
)

target_link_libraries(appTest_Qt_Location
    PRIVATE Qt6::Quick
)

install(TARGETS appTest_Qt_Location
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
