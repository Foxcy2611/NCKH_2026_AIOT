#include "DashboardData.h"

#include <QDateTime>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QTime>
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
{
    insert("gatewayId", 0);
    insert("operatingMode", "OFFLINE");
    insert("uplinkType", "NONE");
    insert("batteryGate", 0);

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
    if (root.value("schema_version").toInt(-1) != 1
        || root.value("message_type").toString() != "complete_packet") {
        if (errorMessage) {
            *errorMessage = QStringLiteral("Sai schema_version hoặc message_type");
        }
        return false;
    }

    if (!root.value("gateway").isObject()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("Thiếu object gateway");
        }
        return false;
    }

    const QJsonObject gate = root.value("gateway").toObject();
    const int sensorMask = gate.value("sensor_valid_mask").toInt(0);
    const QString timestampBasis = gate.value("timestamp_basis").toString("uptime_ms");
    const quint64 gateTimestamp = jsonUnsigned(gate.value("timestamp"));

    insert("gatewayId", jsonUnsigned(gate.value("gateway_id")));
    insert("operatingMode", operatingModeName(gate.value("operating_mode").toInt(-1)));
    insert("uplinkType", uplinkTypeName(gate.value("uplink_type").toInt(-1)));
    insert("batteryGate", gate.value("battery_gate").toInt(0));

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

    insert("latitude", gpsValid ? gate.value("latitude").toDouble() : 0.0);
    insert("longitude", gpsValid ? gate.value("longitude").toDouble() : 0.0);
    insert("gpsTime", gpsValid
               ? formatTimestamp(jsonUnsigned(gate.value("gps_timestamp")), timestampBasis)
               : QStringLiteral("N/A"));

    const bool hasPatientEvent = root.value("has_patient_event").toBool(false);
    insert("hasPatientEvent", hasPatientEvent);

    // Gate-only packet chỉ cập nhật Gateway. Không xóa Patient Event gần nhất.
    if (hasPatientEvent && root.value("node").isObject()) {
        const QJsonObject node = root.value("node").toObject();
        const bool vitalsValid = node.value("vitals_valid").toBool(false);

        insert("sessionId", jsonUnsigned(node.value("session_id")));
        insert("eventTime", formatTimestamp(gateTimestamp, timestampBasis));
        insert("eventType", eventTypeName(node.value("event_type").toInt(-1)));
        insert("classification", classificationName(node.value("classification").toInt(-1)));
        insert("modelScore", node.value("model_score").toDouble(0.0));
        insert("audioQuality", audioQualityName(node.value("audio_quality").toInt(-1)));
        insert("vitalsValid", vitalsValid);
        insert("heartRate", vitalsValid ? node.value("heart_rate").toInt() : 0);
        insert("spo2", vitalsValid ? node.value("spo2").toInt() : 0);
        insert("batteryNode", node.value("battery_node").toInt(0));

        if (vitalsValid) {
            appendHistory("hrHistory", node.value("heart_rate").toDouble());
        }
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
