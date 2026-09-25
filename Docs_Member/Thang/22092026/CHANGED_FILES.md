# Danh sách thay đổi

## Repo hiện tại → bản tích hợp

| Thao tác | Đường dẫn |
|---|---|
| MODIFY | Final_Project_NCKH/Gateway/.gitignore |
| ADD | Final_Project_NCKH/Gateway/README.md |
| MODIFY | Final_Project_NCKH/Gateway/include/Config/gateway_config.h |
| ADD | Final_Project_NCKH/Gateway/include/Config/gateway_network_config.h |
| MODIFY | Final_Project_NCKH/Gateway/include/Config/gateway_types.h |
| MODIFY | Final_Project_NCKH/Gateway/include/Network/Secure_Event_Decryptor.h |
| MODIFY | Final_Project_NCKH/Gateway/include/Network/gateway_espnow.h |
| ADD | Final_Project_NCKH/Gateway/include/Network/gateway_lte.h |
| DELETE | Final_Project_NCKH/Gateway/include/Network/gateway_mqtt.h |
| ADD | Final_Project_NCKH/Gateway/include/Network/gateway_mqtt_lte.h |
| ADD | Final_Project_NCKH/Gateway/include/Network/gateway_mqtt_wifi.h |
| MODIFY | Final_Project_NCKH/Gateway/include/Network/gateway_wifi.h |
| ADD | Final_Project_NCKH/Gateway/include/Secure_Protocol.h |
| ADD | Final_Project_NCKH/Gateway/include/Sensor/ESP32_A7680C_AT.h |
| ADD | Final_Project_NCKH/Gateway/include/Sensor/ESP32_BMP280_Lib.h |
| ADD | Final_Project_NCKH/Gateway/include/Sensor/ESP32_DHT22_Lib.h |
| ADD | Final_Project_NCKH/Gateway/include/Sensor/ESP32_NEO_M8N_GPS.h |
| ADD | Final_Project_NCKH/Gateway/include/Sensor/ESP32_SGP30_Lib.h |
| ADD | Final_Project_NCKH/Gateway/include/System/gateway_json.h |
| ADD | Final_Project_NCKH/Gateway/include/System/gateway_network.h |
| MODIFY | Final_Project_NCKH/Gateway/include/System/gateway_queue.h |
| MODIFY | Final_Project_NCKH/Gateway/include/System/gateway_record.h |
| MODIFY | Final_Project_NCKH/Gateway/include/System/gateway_runtime.h |
| ADD | Final_Project_NCKH/Gateway/include/System/gateway_sensor.h |
| ADD | Final_Project_NCKH/Gateway/include/System/gateway_state.h |
| MODIFY | Final_Project_NCKH/Gateway/include/Task/gateway_tasks.h |
| MODIFY | Final_Project_NCKH/Gateway/platformio.ini |
| MODIFY | Final_Project_NCKH/Gateway/src/Secure_Event_Decryptor.cpp |
| MODIFY | Final_Project_NCKH/Gateway/src/gateway_espnow.cpp |
| ADD | Final_Project_NCKH/Gateway/src/gateway_json.cpp |
| DELETE | Final_Project_NCKH/Gateway/src/gateway_mqtt.cpp |
| MODIFY | Final_Project_NCKH/Gateway/src/gateway_queue.cpp |
| ADD | Final_Project_NCKH/Gateway/src/gateway_state.cpp |
| DELETE | Final_Project_NCKH/Gateway/src/gateway_wifi.cpp |
| MODIFY | Final_Project_NCKH/Gateway/src/main.cpp |
| MODIFY | Final_Project_NCKH/Gateway/src/main_test_sender_espnow.cpp |
| ADD | Final_Project_NCKH/Gateway/src/network/gateway_lte.cpp |
| ADD | Final_Project_NCKH/Gateway/src/network/gateway_mqtt_lte.cpp |
| ADD | Final_Project_NCKH/Gateway/src/network/gateway_mqtt_wifi.cpp |
| ADD | Final_Project_NCKH/Gateway/src/network/gateway_wifi.cpp |
| ADD | Final_Project_NCKH/Gateway/src/sensor/ESP32_A7680C_AT.cpp |
| ADD | Final_Project_NCKH/Gateway/src/sensor/ESP32_BMP280_Lib.cpp |
| ADD | Final_Project_NCKH/Gateway/src/sensor/ESP32_DHT22_Lib.cpp |
| ADD | Final_Project_NCKH/Gateway/src/sensor/ESP32_NEO_M8N_GPS.cpp |
| ADD | Final_Project_NCKH/Gateway/src/sensor/ESP32_SGP30_Lib.cpp |
| ADD | Final_Project_NCKH/Gateway/src/task/task_conn_manager.cpp |
| ADD | Final_Project_NCKH/Gateway/src/task/task_espnow.cpp |
| ADD | Final_Project_NCKH/Gateway/src/task/task_gateway_manager.cpp |
| ADD | Final_Project_NCKH/Gateway/src/task/task_mqtt_publisher.cpp |
| ADD | Final_Project_NCKH/Gateway/src/task/task_sensor.cpp |
| DELETE | Final_Project_NCKH/Gateway/src/task_espnow.cpp |
| DELETE | Final_Project_NCKH/Gateway/src/task_gateway_manager.cpp |
| DELETE | Final_Project_NCKH/Gateway/src/task_sensor.cpp |
| MODIFY | Final_Project_NCKH/Gateway/test/native/Arduino.h |
| DELETE | Final_Project_NCKH/Gateway/test/native/RESULT.txt |
| ADD | Final_Project_NCKH/Gateway/test/native/RESULT_CURRENT.txt |
| ADD | Final_Project_NCKH/Gateway/test/native/run_tests.py |
| ADD | Final_Project_NCKH/Gateway/test/native/test_json.cpp |
| MODIFY | Final_Project_NCKH/Gateway/test/native/test_record.cpp |
| ADD | Final_Project_NCKH/Gateway/test/native/test_wifi.cpp |
| ADD | Final_Project_NCKH/Gateway/test/native/wifi_mock/Arduino.h |
| ADD | Final_Project_NCKH/Gateway/test/native/wifi_mock/WiFi.h |
| ADD | Final_Project_NCKH/Gateway/test/native/wifi_mock/esp_wifi.h |
| ADD | Final_Project_NCKH/Gateway/tools/check_shared_protocol.py |

Thêm tài liệu Docs_Member/M4_Latest_State/. Không sửa các project khác.

## Gateway_old → Gateway(5)

| Thao tác | Đường dẫn trong Gateway |
|---|---|
| MODIFY | README.md |
| DELETE | docs/BUILD_PHASE_1_3.log |
| DELETE | docs/CHANGED_FILES.txt |
| DELETE | docs/CHANGES_PHASE_1_3.txt |
| DELETE | docs/FINAL_HANDOFF_PHASE_3_6.md |
| DELETE | docs/M4_M5_WIFI_SCHEMA.md |
| DELETE | docs/M4_TEST_AND_HANDOFF.md |
| DELETE | docs/PHASE_1_3_WIFI_GUIDE.md |
| DELETE | docs/PHASE_3_6_GUIDE.md |
| DELETE | docs/VALIDATION_PHASE_1_3.md |
| DELETE | docs/VALIDATION_PHASE_3_6.md |
| DELETE | docs/examples/patient_event.json |
| DELETE | docs/examples/telemetry.json |
| MODIFY | include/Config/gateway_config.h |
| MODIFY | include/Config/gateway_network_config.h |
| MODIFY | include/Config/gateway_types.h |
| MODIFY | include/Network/Secure_Event_Decryptor.h |
| ADD | include/Secure_Protocol.h |
| MODIFY | include/System/gateway_json.h |
| MODIFY | include/System/gateway_queue.h |
| MODIFY | include/System/gateway_record.h |
| ADD | include/System/gateway_state.h |
| DELETE | include/System/gateway_storage.h |
| MODIFY | platformio.ini |
| MODIFY | src/Secure_Event_Decryptor.cpp |
| MODIFY | src/gateway_espnow.cpp |
| MODIFY | src/gateway_json.cpp |
| MODIFY | src/gateway_queue.cpp |
| ADD | src/gateway_state.cpp |
| DELETE | src/gateway_storage.cpp |
| MODIFY | src/main.cpp |
| MODIFY | src/main_test_sender_espnow.cpp |
| MODIFY | src/task/task_espnow.cpp |
| MODIFY | src/task/task_gateway_manager.cpp |
| MODIFY | src/task/task_mqtt_publisher.cpp |
| DELETE | test/native/RESULT.txt |
| ADD | test/native/RESULT_CURRENT.txt |
| DELETE | test/native/RESULT_PHASE_1_3.txt |
| DELETE | test/native/RESULT_PHASE_3_6.txt |
| MODIFY | test/native/run_tests.py |
| MODIFY | test/native/test_json.cpp |
| MODIFY | test/native/test_record.cpp |
