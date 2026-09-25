#include "Sensor/ESP32_NEO_M8N_GPS.h"

static HardwareSerial* gpsSerial;

uint64_t NEO_M8N_UnixTimeMs(const NEO_Data_t* value){
    if(!value || value->year < 1970 || value->month < 1 || value->month > 12
       || value->day < 1 || value->day > 31) return 0;
    int y = value->year;
    unsigned m = value->month, d = value->day;
    y -= m <= 2;
    const int era = (y >= 0 ? y : y - 399) / 400;
    const unsigned yoe = (unsigned)(y - era * 400);
    const unsigned mp = m > 2 ? m - 3 : m + 9;
    const unsigned doy = (153 * mp + 2) / 5 + d - 1;
    const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    const int64_t days = era * 146097LL + (int64_t)doe - 719468LL;
    if(days < 0) return 0;
    const uint64_t seconds = (uint64_t)days * 86400ULL
        + value->hour * 3600ULL + value->minute * 60ULL + value->second;
    return seconds * 1000ULL;
}

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
                char *star = strchr(buff, '*');
                if(!star || strlen(star + 1) < 2) continue;
                uint8_t calculated = 0;
                for(char *p = buff + 1; p < star; ++p) calculated ^= (uint8_t)*p;
                const uint8_t received = (uint8_t)strtoul(star + 1, nullptr, 16);
                if(calculated != received) continue;
                *star = '\0';

                // Split manually so empty NMEA fields keep their index. strtok()
                // collapses consecutive commas and can shift date/course fields.
                char *fields[16] = {};
                size_t fieldCount = 1;
                fields[0] = buff;
                for(char *p = buff; *p && fieldCount < 16; ++p){
                    if(*p == ',') { *p = '\0'; fields[fieldCount++] = p + 1; }
                }
                if(fieldCount < 10 || fields[2][0] != 'A') continue;
                if(strlen(fields[1]) < 6 || !fields[3][0] || !fields[4][0]
                   || !fields[5][0] || !fields[6][0] || strlen(fields[9]) != 6) continue;

                char temp[3] = {0};
                memcpy(temp, fields[1], 2); gpsData->hour = atoi(temp);
                memcpy(temp, fields[1] + 2, 2); gpsData->minute = atoi(temp);
                memcpy(temp, fields[1] + 4, 2); gpsData->second = atoi(temp);
                memcpy(temp, fields[9], 2); gpsData->day = atoi(temp);
                memcpy(temp, fields[9] + 2, 2); gpsData->month = atoi(temp);
                memcpy(temp, fields[9] + 4, 2); gpsData->year = atoi(temp) + 2000;
                gpsData->latitude = Convert_NMEA_2Decimal(fields[3], fields[4][0]);
                gpsData->longitude = Convert_NMEA_2Decimal(fields[5], fields[6][0]);
                gpsData->speed_kmh = fields[7][0] ? atof(fields[7]) * 1.852f : 0.0f;
                gpsData->isValid = gpsData->latitude >= -90.0f && gpsData->latitude <= 90.0f
                    && gpsData->longitude >= -180.0f && gpsData->longitude <= 180.0f;
                if(gpsData->isValid) return true;
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
