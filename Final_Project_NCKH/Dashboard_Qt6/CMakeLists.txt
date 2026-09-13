cmake_minimum_required(VERSION 3.16)

project(
    Dashboard_Qt6
    VERSION 0.1
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(
    Qt6
    REQUIRED COMPONENTS
        Qml
        Quick
        QuickControls2
)

qt_standard_project_setup(REQUIRES 6.8)

# Frontend executable + QML module
add_subdirectory(ui)

# Backend libraries will be enabled later.
# add_subdirectory(libs/model)
# add_subdirectory(libs/dashboard)
# add_subdirectory(libs/mqtt)
# add_subdirectory(libs/parser)
# add_subdirectory(libs/storage)
