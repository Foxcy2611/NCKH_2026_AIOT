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
        Mqtt
        Network
)

qt_standard_project_setup(REQUIRES 6.8)

# Frontend executable + QML module
add_subdirectory(ui)

# Copy cấu hình ra cạnh file chạy. Có thể dùng biến môi trường NCKH_MQTT_*
# để ghi đè mà không phải lưu mật khẩu vào source.
set(MQTT_CONFIG_SOURCE ${CMAKE_CURRENT_SOURCE_DIR}/config/mqtt_config.json)
if(NOT EXISTS ${MQTT_CONFIG_SOURCE})
    set(MQTT_CONFIG_SOURCE ${CMAKE_CURRENT_SOURCE_DIR}/config/mqtt_config.example.json)
endif()

configure_file(
    ${MQTT_CONFIG_SOURCE}
    ${CMAKE_CURRENT_BINARY_DIR}/mqtt_config.json
    COPYONLY
)
