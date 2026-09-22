#include "ESP32_NEO_M8N_GPS.h"

static HardwareSerial* gpsSerial;

// Kinh độ Vĩ độ dùng đơn vị độ và phút
// Convert sang độ thập phân, đơn vị sử dụng trong GG Maps
// ddmm.mmmm
static float Convert_NMEA_2Decimal(char* nmeaCoord, char direction){
    if(strlen(nmeaCoord) < 5) return 0.0f;

    // Tìm vị trí dấu ., return về con trỏ
    char *dotPos = strchr(nmeaCoord, '.');
    if(! dotPos) return 0.0f;

    // Vdu: 4807.038
    // Tách phần độ: dd
    // Vị trí dấu . - đầu chuỗi
    int degree_len = (dotPos - nmeaCoord) - 2; // (4 - 0) - 2 = 2
    char degStr[4] = {0}; // 4 8
    strncpy(degStr, nmeaCoord, degree_len);

    
    // Ép sang số
    float degrees = atof(degStr); // 48
    float minutes = atof(dotPos - 2); // 07.038 = 7.038

    float decimal = degrees + (minutes / 60.0f);

    // Xử lý tọa độ cho Nam / Tây Bán Cầu
    if(direction == 'S' || direction == 'W'){
        decimal = -decimal;
    }

    return decimal;
}

// &Serial1
void NEO_M8N_Init(HardwareSerial* serialPort){
    gpsSerial = serialPort;
}

bool NEO_M8N_ReadData(NEO_Data_t* gpsData){
    static char buff[128];
    static uint8_t buff_idx = 0;

    // Đọc toàn bộ - Sử dụng \n làm ký tự kết thúc
    while(gpsSerial->available()){
        char c = gpsSerial->read();

        if(c == '\n'){
            buff[buff_idx] = '\0';
            buff_idx = 0;

            if(strncmp(buff, "$GNRMC", 6) == 0 || strncmp(buff, "$GPRMC", 6) == 0){
                char* token = strtok(buff, ",");
                int field = 0;
                
                // Các biến tạm để lưu chuỗi Vĩ độ / Kinh độ
                char latStr[20] = "", lonStr[20] = "";
                char latDir = 'N', lonDir = 'E';

                while(token != NULL){
                    field++;

                    switch(field){
                        // UTC: hhmmss.ss
                        // 123519 = 12h 35m 19s
                        case 2: 
                            if(strlen(token) >= 6){
                                char temp[3] = {0};
                                strncpy(temp, token, 2);
                                gpsData->hour = atoi(temp);
                                strncpy(temp, token + 2, 2);
                                gpsData->minute = atoi(temp);
                                strncpy(temp, token + 4, 2);
                                gpsData->second = atoi(temp);
                            }
                            break;

                        // Cờ trạng thái
                        case 3:
                            gpsData->isValid = (token[0] == 'A');
                            break;

                        // Vĩ độ thô
                        case 4:         
                            strcpy(latStr, token);
                            break;
                            
                        // Hướng vĩ độ N/S
                        case 5:
                            latDir = token[0];
                            break;

                        // Kinh độ thô
                        case 6:
                            strcpy(lonStr, token);
                            break;

                        // Hướng kinh độ W/E
                        case 7:
                            lonDir = token[0];
                            break;

                        // Tốc độ di chuyển
                        case 8:
                            gpsData->speed_kmh = atof(token) * 1.852f;
                            break;

                        // Ngày tháng năm ddmmyy
                        case 10:
                            if(strlen(token) == 6){
                                char temp[3] = {0};
                                strncpy(temp, token, 2); 
                                gpsData->day = atoi(temp);
                                strncpy(temp, token + 2, 2); 
                                gpsData->month = atoi(temp);
                                strncpy(temp, token + 4, 2); 
                                gpsData->year = atoi(temp) + 2000;
                            }
                            break;
                    }
                    token = strtok(NULL, ",");
                }

                if(gpsData->isValid){
                    gpsData->latitude  = Convert_NMEA_2Decimal(latStr, latDir);
                    gpsData->longitude = Convert_NMEA_2Decimal(lonStr, lonDir);
                    return true;
                }
            }
            // Bỏ qua ký tự \r và chống tràn mảng
        } else if(c != '\r' && buff_idx < 127){
            buff[buff_idx++] = c;
        }
    }

    return false;
}

// ==== TEST MAIN ====
NEO_Data_t myGPS;
void NEO_M8N_TestSetup(void){
    // Lưu ý: Nếu ở hàm setup() chính đã gọi Serial.begin(115200) thì bỏ dòng dưới đi
    Serial.begin(115200); 
    
    Serial1.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
    NEO_M8N_Init(&Serial1);
    
    Serial.println("\n--- NEO-M8N GPS Test ---");
    Serial.println("[INFO] Dang tim ve tinh... Hay mang ra ngoai troi!");
}

void NEO_M8N_TestLoop(void){
    if (NEO_M8N_ReadData(&myGPS)) {
        // Xử lý múi giờ VN
        int local_hour = myGPS.hour + 7;
        int local_day = myGPS.day;
        if(local_hour >= 24) {
            local_hour -= 24;
            local_day += 1;
        }

        Serial.println("\n[GPS FIXED] ---------------------------");
        Serial.printf("Thoi gian: %02d:%02d:%02d - Ngay: %02d/%02d/%d\n", 
                      local_hour, myGPS.minute, myGPS.second, 
                      local_day, myGPS.month, myGPS.year);
        Serial.printf("Vi tri   : %.6f, %.6f\n", myGPS.latitude, myGPS.longitude);
        Serial.printf("Toc do   : %.2f km/h\n", myGPS.speed_kmh);
        Serial.println("---------------------------------------");
    }
}