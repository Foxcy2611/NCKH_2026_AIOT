#include "DashboardData.h"

#include <QDateTime>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QTime>
#include <QUrl>
#include <QUrlQuery>
#include <QVariantList>

namespace {

constexpr int SensorDht22Valid = 1 << 0;
constexpr int SensorBmp280Valid = 1 << 1;
constexpr int SensorSgp30Valid = 1 << 2;
constexpr int SensorGpsValid = 1 << 3;
constexpr int MaximumHistorySize = 14;

quint64 jsonUnsigned(const QJsonValue &value)
{
    return value.toVariant().toULongLong();
}

} // namespace

DashboardData::DashboardData(QObject *parent)
    : QQmlPropertyMap(this, parent)
    , m_googleMapsApiKey(qEnvironmentVariable("NCKH_GOOGLE_MAPS_API_KEY"))
{
    insert("gatewayId", 0);
    insert("operatingMode", "OFFLINE");
    insert("uplinkType", "NONE");
    insert("batteryGate", 0);
    insert("batteryGateAvailable", false);

    insert("temperature", 0.0);
    insert("humidity", 0.0);
    insert("pressure", 0.0);
    insert("tvoc", 0);
    insert("eco2", 0);

    insert("dhtValid", false);
    insert("bmpValid", false);
    insert("sgpValid", false);
    insert("gpsValid", false);

    insert("wifiConnected", false);
    insert("wifiRssi", -127);
    insert("lteRegistered", false);
    insert("lteRssi", -127);
    insert("mqttConnected", false);
    insert("gatewayMqttConnected", false);

    insert("latitude", 0.0);
    insert("longitude", 0.0);
    insert("gpsTime", "N/A");
    insert("hasMapLocation", false);
    insert("googleMapsConfigured", !m_googleMapsApiKey.isEmpty());
    insert("googleStaticMapUrl", QString{});
    insert("googleMapsUrl", QString{});

    insert("hasPatientEvent", false);
    insert("sessionId", 0);
    insert("eventTime", "N/A");
    insert("eventType", "N/A");
    insert("classification", "N/A");
    insert("modelScore", 0.0);
    insert("audioQuality", "N/A");
    insert("vitalsValid", false);
    insert("heartRate", 0);
    insert("spo2", 0);
    insert("batteryNode", 0);

    insert("tempHistory", QVariantList{});
    insert("humHistory", QVariantList{});
    insert("hrHistory", QVariantList{});
    insert("backendStatus", "Chưa kết nối MQTT");
    insert("lastMessageTime", "N/A");
}

bool DashboardData::applyCompletePacketJson(const QByteArray &json, QString *errorMessage)
{
    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(json, &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("JSON không hợp lệ: %1").arg(parseError.errorString());
        }
        return false;
    }

    const QJsonObject root = document.object();
    const int schemaVersion = root.value("schema_version").toInt(-1);
    const QString messageType = root.value("message_type").toString();
    const bool completePacket = schemaVersion == 1
                                && messageType == QStringLiteral("complete_packet");
    const bool legacyDashboardSnapshot = schemaVersion == 2
                                         && messageType == QStringLiteral("dashboard_snapshot");
    if (!completePacket && !legacyDashboardSnapshot) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("Không hỗ trợ schema_version=%1, message_type=%2")
                                .arg(schemaVersion)
                                .arg(messageType);
        }
        return false;
    }

    // Schema chính dùng gate/patient_event. Vẫn nhận gateway/node của dữ liệu
    // thử nghiệm cũ để không làm hỏng file JSON đã lưu trước khi chốt schema.
    const QString gateKey = root.value(QStringLiteral("gate")).isObject()
                                ? QStringLiteral("gate")
                                : QStringLiteral("gateway");
    const QString patientKey = root.contains(QStringLiteral("patient_event"))
                                   ? QStringLiteral("patient_event")
                                   : QStringLiteral("node");

    if (!root.value(gateKey).isObject()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("Thiếu object %1").arg(gateKey);
        }
        return false;
    }

    const QJsonObject gate = root.value(gateKey).toObject();
    const int sensorMask = gate.value("sensor_valid_mask").toInt(0);
    const QString timestampBasis = gate.value("time_basis").toString(
        gate.value("timestamp_basis").toString("uptime_ms"));
    const quint64 gateTimestamp = jsonUnsigned(gate.value("timestamp"));

    insert("gatewayId", jsonUnsigned(gate.value("gateway_id")));
    insert("operatingMode", operatingModeName(gate.value("operating_mode").toInt(-1)));
    insert("uplinkType", uplinkTypeName(gate.value("uplink_type").toInt(-1)));
    // Schema hiện chưa truyền pin Gateway; không ghi đè giá trị cũ thành 0.
    if (gate.contains("battery_gate") && !gate.value("battery_gate").isNull()) {
        insert("batteryGate", gate.value("battery_gate").toInt(0));
        insert("batteryGateAvailable", true);
    } else {
        insert("batteryGateAvailable", false);
    }

    const bool dhtValid = (sensorMask & SensorDht22Valid) != 0;
    const bool bmpValid = (sensorMask & SensorBmp280Valid) != 0;
    const bool sgpValid = (sensorMask & SensorSgp30Valid) != 0;
    const bool gpsValid = (sensorMask & SensorGpsValid) != 0;
    insert("dhtValid", dhtValid);
    insert("bmpValid", bmpValid);
    insert("sgpValid", sgpValid);
    insert("gpsValid", gpsValid);

    const double temperature = dhtValid ? gate.value("temperature").toDouble() : 0.0;
    const double humidity = dhtValid ? gate.value("humidity").toDouble() : 0.0;
    const double pressure = bmpValid ? gate.value("pressure").toDouble() : 0.0;
    insert("temperature", temperature);
    insert("humidity", humidity);
    insert("pressure", pressure);
    insert("tvoc", sgpValid ? gate.value("tvoc").toInt() : 0);
    insert("eco2", sgpValid ? gate.value("eco2").toInt() : 0);
    if (dhtValid) {
        appendHistory("tempHistory", temperature);
        appendHistory("humHistory", humidity);
    }

    insert("wifiConnected", gate.value("wifi_connected").toBool(false));
    insert("wifiRssi", gate.value("wifi_rssi_dbm").toInt(-127));
    insert("lteRegistered", gate.value("lte_registered").toBool(false));
    insert("lteRssi", gate.value("lte_rssi_dbm").toInt(-127));
    insert("gatewayMqttConnected", gate.value("mqtt_connected").toBool(false));

    if (gpsValid) {
        const double latitude = gate.value("latitude").toDouble();
        const double longitude = gate.value("longitude").toDouble();
        const bool coordinateValid = latitude >= -90.0 && latitude <= 90.0
                                     && longitude >= -180.0 && longitude <= 180.0
                                     && !(qFuzzyIsNull(latitude) && qFuzzyIsNull(longitude));
        if (coordinateValid) {
            insert("latitude", latitude);
            insert("longitude", longitude);
            insert("hasMapLocation", true);
            updateGoogleMap(latitude, longitude);
        }
    }
    if (gpsValid && !gate.value("gps_timestamp").isNull()) {
        const quint64 gpsTimestamp = jsonUnsigned(gate.value("gps_timestamp"));
        const QString gpsBasis = gpsTimestamp >= 1000000000000ULL
                                     ? QStringLiteral("epoch_ms")
                                     : timestampBasis;
        insert("gpsTime", formatTimestamp(gpsTimestamp, gpsBasis));
    } else {
        insert("gpsTime", QStringLiteral("N/A"));
    }

    const bool hasPatientEvent = root.value("has_patient_event").toBool(false);
    insert("hasPatientEvent", hasPatientEvent);

    // Không có Patient Event thì chỉ cập nhật Gateway, không xóa kết quả Node gần nhất.
    if (hasPatientEvent && root.value(patientKey).isObject()) {
        const QJsonObject node = root.value(patientKey).toObject();
        const bool vitalsValid = node.value("vitals_valid").toBool(false);
        const quint64 sessionId = jsonUnsigned(node.value("session_id"));
        QString eventId = root.value("event_id").toString();
        if (eventId.isEmpty()) {
            eventId = QStringLiteral("legacy-session-%1").arg(sessionId);
        }
        const bool isNewPatientEvent = eventId != m_lastPatientEventId;

        quint64 eventTimestamp = gateTimestamp;
        QString eventTimestampBasis = timestampBasis;
        if (root.value("source").isObject()) {
            eventTimestamp = jsonUnsigned(
                root.value("source").toObject().value("received_uptime_ms"));
            eventTimestampBasis = QStringLiteral("uptime_ms");
        }

        insert("sessionId", sessionId);
        insert("eventTime", formatTimestamp(eventTimestamp, eventTimestampBasis));
        insert("eventType", eventTypeName(node.value("event_type").toInt(-1)));
        insert("classification", classificationName(node.value("classification").toInt(-1)));
        insert("modelScore", node.value("model_score").toDouble(0.0));
        insert("audioQuality", audioQualityName(node.value("audio_quality").toInt(-1)));
        insert("vitalsValid", vitalsValid);
        insert("heartRate", vitalsValid ? node.value("heart_rate").toInt() : 0);
        insert("spo2", vitalsValid ? node.value("spo2").toInt() : 0);
        insert("batteryNode", node.value("battery_node").toInt(0));

        if (isNewPatientEvent && vitalsValid) {
            appendHistory("hrHistory", node.value("heart_rate").toDouble());
        }
        m_lastPatientEventId = eventId;
    }

    insert("lastMessageTime", QDateTime::currentDateTime().toString("HH:mm:ss"));
    insert("backendStatus", "Đang nhận dữ liệu MQTT");
    return true;
}

void DashboardData::setTransportConnected(bool connected, const QString &status)
{
    insert("mqttConnected", connected);
    insert("backendStatus", status);
}

QString DashboardData::operatingModeName(int value)
{
    switch (value) {
    case 0: return QStringLiteral("HOME");
    case 1: return QStringLiteral("OFFLINE");
    case 2: return QStringLiteral("MOBILE");
    default: return QStringLiteral("UNKNOWN");
    }
}

QString DashboardData::uplinkTypeName(int value)
{
    switch (value) {
    case 0: return QStringLiteral("NONE");
    case 1: return QStringLiteral("Wi-Fi");
    case 2: return QStringLiteral("LTE");
    default: return QStringLiteral("UNKNOWN");
    }
}

QString DashboardData::eventTypeName(int value)
{
    switch (value) {
    case 0: return QStringLiteral("Manual Check");
    case 1: return QStringLiteral("Monitor Event");
    default: return QStringLiteral("Unknown Event");
    }
}

QString DashboardData::classificationName(int value)
{
    switch (value) {
    case 0: return QStringLiteral("Asthma-like");
    case 1: return QStringLiteral("Non-asthma");
    case 2: return QStringLiteral("Unsure");
    default: return QStringLiteral("Unknown");
    }
}

QString DashboardData::audioQualityName(int value)
{
    switch (value) {
    case 0: return QStringLiteral("GOOD");
    case 1: return QStringLiteral("TOO WEAK");
    case 2: return QStringLiteral("TOO LOUD");
    case 3: return QStringLiteral("INACTIVE");
    default: return QStringLiteral("UNKNOWN");
    }
}

QString DashboardData::formatTimestamp(quint64 timestampMs, const QString &basis)
{
    if (basis == "epoch_ms" || timestampMs >= 1000000000000ULL) {
        return QDateTime::fromMSecsSinceEpoch(static_cast<qint64>(timestampMs))
            .toLocalTime().toString("HH:mm:ss");
    }

    const quint64 totalSeconds = timestampMs / 1000ULL;
    const quint64 hours = (totalSeconds / 3600ULL) % 24ULL;
    const quint64 minutes = (totalSeconds / 60ULL) % 60ULL;
    const quint64 seconds = totalSeconds % 60ULL;
    return QStringLiteral("Uptime %1:%2:%3")
        .arg(hours, 2, 10, QLatin1Char('0'))
        .arg(minutes, 2, 10, QLatin1Char('0'))
        .arg(seconds, 2, 10, QLatin1Char('0'));
}

void DashboardData::appendHistory(const QString &key, double number)
{
    QVariantList history = value(key).toList();
    history.append(number);
    while (history.size() > MaximumHistorySize) {
        history.removeFirst();
    }
    insert(key, history);
}

void DashboardData::updateGoogleMap(double latitude, double longitude)
{
    const QString coordinate = QStringLiteral("%1,%2")
                                   .arg(latitude, 0, 'f', 6)
                                   .arg(longitude, 0, 'f', 6);

    QUrl interactiveUrl(QStringLiteral("https://www.google.com/maps/search/"));
    QUrlQuery interactiveQuery;
    interactiveQuery.addQueryItem(QStringLiteral("api"), QStringLiteral("1"));
    interactiveQuery.addQueryItem(QStringLiteral("query"), coordinate);
    interactiveUrl.setQuery(interactiveQuery);
    insert("googleMapsUrl", interactiveUrl.toString(QUrl::FullyEncoded));

    if (m_googleMapsApiKey.isEmpty()) {
        insert("googleStaticMapUrl", QString{});
        return;
    }

    QUrl staticMapUrl(QStringLiteral("https://maps.googleapis.com/maps/api/staticmap"));
    QUrlQuery staticMapQuery;
    staticMapQuery.addQueryItem(QStringLiteral("center"), coordinate);
    staticMapQuery.addQueryItem(QStringLiteral("zoom"), QStringLiteral("16"));
    staticMapQuery.addQueryItem(QStringLiteral("size"), QStringLiteral("640x480"));
    staticMapQuery.addQueryItem(QStringLiteral("scale"), QStringLiteral("2"));
    staticMapQuery.addQueryItem(QStringLiteral("maptype"), QStringLiteral("roadmap"));
    staticMapQuery.addQueryItem(QStringLiteral("markers"),
                                QStringLiteral("color:blue|label:G|%1").arg(coordinate));
    staticMapQuery.addQueryItem(QStringLiteral("key"), m_googleMapsApiKey);
    staticMapUrl.setQuery(staticMapQuery);
    insert("googleStaticMapUrl", staticMapUrl.toString(QUrl::FullyEncoded));
}
