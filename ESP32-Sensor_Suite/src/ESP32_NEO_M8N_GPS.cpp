#include "ESP32_NEO_M8N_GPS.h"

static HardwareSerial* gpsSerial;

// Kinh độ Vĩ độ dùng đơn vị độ và phút
// Convert sang độ thập phân, đơn vị sử dụng trong GG Maps
// ddmm.mmmm
static float Convert_NMEA_2Decimal(const char* nmeaCoord, char direction){
    if(!nmeaCoord) return 0.0f;
    if(strlen(nmeaCoord) < 5) return 0.0f;

    // Tìm vị trí dấu ., return về con trỏ
    const char *dotPos = strchr(nmeaCoord, '.');
    if(! dotPos) return 0.0f;

    // ddmm.mmmm or dddmm.mmmm
    int degree_len = (int)(dotPos - nmeaCoord) - 2;
    if(degree_len <= 0) return 0.0f;

    char degStr[8] = {0};
    if(degree_len >= (int)sizeof(degStr)) degree_len = (int)sizeof(degStr) - 1;
    strncpy(degStr, nmeaCoord, degree_len);
    degStr[degree_len] = '\0';

    float degrees = atof(degStr);
    // minutes start at dotPos - 2
    char minBuf[16] = {0};
    const char* minStart = dotPos - 2;
    size_t minLen = strlen(minStart);
    if(minLen >= sizeof(minBuf)) minLen = sizeof(minBuf) - 1;
    strncpy(minBuf, minStart, minLen);
    minBuf[minLen] = '\0';
    float minutes = atof(minBuf);

    float decimal = degrees + (minutes / 60.0f);

    if(direction == 'S' || direction == 'W') decimal = -decimal;
    return decimal;
}

// &Serial1
void NEO_M8N_Init(HardwareSerial* serialPort){
    gpsSerial = serialPort;
}

bool NEO_M8N_ReadData(NEO_Data_t* gpsData){
    static char buff[128];
    static uint8_t buff_idx = 0;

    // Kiểm tra gpsSerial đã init chưa
    if(gpsSerial == nullptr) return false;

    // Khởi tạo giá trị mặc định để tránh giữ giá trị cũ
    if(gpsData){
        gpsData->isValid = false;
        gpsData->latitude = 0.0f;
        gpsData->longitude = 0.0f;
        gpsData->speed_kmh = 0.0f;
        gpsData->hour = gpsData->minute = gpsData->second = 0;
        gpsData->day = gpsData->month = 0;
        gpsData->year = 0;
    }

    // Đọc toàn bộ - Sử dụng \n làm ký tự kết thúc
    while(gpsSerial->available()){
        char c = gpsSerial->read();

        if(c == '\n'){
            buff[buff_idx] = '\0';
            buff_idx = 0;

            if(strncmp(buff, "$GNRMC", 6) == 0 || strncmp(buff, "$GPRMC", 6) == 0){
                // Debug: in câu NMEA nhận được
                Serial.print("[GPS RAW] "); Serial.println(buff);
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
                            strncpy(latStr, token, sizeof(latStr)-1);
                            latStr[sizeof(latStr)-1] = '\0';
                            break;
                            
                        // Hướng vĩ độ N/S
                        case 5:
                            latDir = token[0];
                            break;

                        // Kinh độ thô
                        case 6:
                            strncpy(lonStr, token, sizeof(lonStr)-1);
                            lonStr[sizeof(lonStr)-1] = '\0';
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

static NEO_Data_t gpsData;
void Test_Setup(void){
    Serial.begin(115200);
    delay(1000);

    // Khởi tạo UART cho GPS
    Serial1.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);

    // Truyền cổng UART cho driver GPS
    NEO_M8N_Init(&Serial1);

    Serial.println("\n--- GPS Test Main ---");
    Serial.println("Dang khoi dong GPS, vui long cho 1-2 phut de bat fix ve tinh...");
}

void Test_Loop(void){
    // Đọc và xử lý dữ liệu GPS
    if (NEO_M8N_ReadData(&gpsData)) {

        // UTC -> giờ Việt Nam
        int local_hour = gpsData.hour + 7;
        int local_day = gpsData.day;

        if (local_hour >= 24) {
            local_hour -= 24;
            local_day += 1;
        }

        Serial.println("\n[GPS FIXED] ---------------------------");

        Serial.printf(
            "Thoi gian: %02d:%02d:%02d - Ngay: %02d/%02d/%d\n",
            local_hour,
            gpsData.minute,
            gpsData.second,
            local_day,
            gpsData.month,
            gpsData.year
        );

        Serial.printf(
            "Vi tri   : %.6f, %.6f\n",
            gpsData.latitude,
            gpsData.longitude
        );

        Serial.printf(
            "Toc do   : %.2f km/h\n",
            gpsData.speed_kmh
        );

        Serial.println("---------------------------------------");
    }

    delay(1000);
}