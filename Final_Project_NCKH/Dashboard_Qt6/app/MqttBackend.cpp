#include "MqttBackend.h"

#include "DashboardData.h"

#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QLoggingCategory>
#include <QSslConfiguration>
#include <QUuid>

namespace {

QString environmentOrValue(const char *name, const QString &fallback)
{
    return qEnvironmentVariableIsSet(name) ? qEnvironmentVariable(name) : fallback;
}

} // namespace

MqttBackend::MqttBackend(DashboardData *dashboardData, QObject *parent)
    : QObject(parent)
    , m_dashboardData(dashboardData)
{
    m_reconnectTimer.setSingleShot(true);
    m_reconnectTimer.setInterval(5000);

    connect(&m_reconnectTimer, &QTimer::timeout, this, &MqttBackend::connectToBroker);

    connect(&m_client, &QMqttClient::connected, this, [this]() {
        m_dashboardData->setTransportConnected(true, QStringLiteral("MQTT đã kết nối"));
        qInfo() << "[MQTT] Connected to" << m_settings.host << "topic" << m_settings.topic;

        QMqttSubscription *subscription = m_client.subscribe(QMqttTopicFilter(m_settings.topic), 0);
        if (!subscription) {
            qWarning() << "[MQTT] Cannot subscribe to" << m_settings.topic;
            m_dashboardData->setTransportConnected(false, QStringLiteral("Không subscribe được topic"));
            m_client.disconnectFromHost();
        }
    });

    connect(&m_client, &QMqttClient::disconnected, this, [this]() {
        m_dashboardData->setTransportConnected(false, QStringLiteral("MQTT mất kết nối"));
        qWarning() << "[MQTT] Disconnected; retry in 5 seconds";
        scheduleReconnect();
    });

    connect(&m_client, &QMqttClient::errorChanged, this, [this](QMqttClient::ClientError error) {
        if (error != QMqttClient::NoError) {
            qWarning() << "[MQTT] Client error:" << error;
        }
    });

    connect(&m_client, &QMqttClient::messageReceived, this,
            [this](const QByteArray &message, const QMqttTopicName &topic) {
        if (topic.name() != m_settings.topic) {
            return;
        }

        QString parserError;
        if (!m_dashboardData->applyCompletePacketJson(message, &parserError)) {
            qWarning() << "[JSON] Rejected packet:" << parserError;
            return;
        }
        qInfo() << "[JSON] Complete packet accepted, bytes=" << message.size();
    });
}

bool MqttBackend::start(const QString &configPath)
{
    QString errorMessage;
    if (!loadSettings(configPath, &errorMessage)) {
        qCritical() << "[MQTT]" << errorMessage;
        m_dashboardData->setTransportConnected(false, errorMessage);
        return false;
    }

    m_client.setHostname(m_settings.host);
    m_client.setPort(m_settings.port);
    m_client.setUsername(m_settings.username);
    m_client.setPassword(m_settings.password);
    m_client.setProtocolVersion(QMqttClient::MQTT_3_1_1);
    m_client.setKeepAlive(30);
    m_client.setCleanSession(true);
    m_client.setClientId(QStringLiteral("DashboardQt6-%1")
                             .arg(QUuid::createUuid().toString(QUuid::Id128).left(12)));

    m_started = true;
    connectToBroker();
    return true;
}

bool MqttBackend::loadSettings(const QString &configPath, QString *errorMessage)
{
    QFile file(configPath);
    if (!file.open(QIODevice::ReadOnly)) {
        *errorMessage = QStringLiteral("Không mở được cấu hình MQTT: %1").arg(configPath);
        return false;
    }

    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
        *errorMessage = QStringLiteral("Cấu hình MQTT không phải JSON hợp lệ: %1")
                            .arg(parseError.errorString());
        return false;
    }

    const QJsonObject object = document.object();
    m_settings.host = environmentOrValue("NCKH_MQTT_HOST", object.value("host").toString());
    m_settings.port = static_cast<quint16>(
        environmentOrValue("NCKH_MQTT_PORT", QString::number(object.value("port").toInt(8883)))
            .toUShort());
    m_settings.username = environmentOrValue("NCKH_MQTT_USERNAME",
                                              object.value("username").toString());
    m_settings.password = environmentOrValue("NCKH_MQTT_PASSWORD",
                                              object.value("password").toString());
    m_settings.topic = environmentOrValue("NCKH_MQTT_TOPIC", object.value("topic").toString());
    m_settings.tls = object.value("tls").toBool(true);

    if (m_settings.host.isEmpty() || m_settings.topic.isEmpty()
        || m_settings.username.isEmpty() || m_settings.password.isEmpty()
        || m_settings.password == "CHANGE_ME") {
        *errorMessage = QStringLiteral("Thiếu host/topic/tài khoản trong mqtt_config.json");
        return false;
    }
    return true;
}

void MqttBackend::connectToBroker()
{
    if (!m_started || m_client.state() != QMqttClient::Disconnected) {
        return;
    }

    m_dashboardData->setTransportConnected(false, QStringLiteral("Đang kết nối MQTT..."));
    qInfo() << "[MQTT] Connecting to" << m_settings.host << ':' << m_settings.port;
    if (m_settings.tls) {
        m_client.connectToHostEncrypted(QSslConfiguration::defaultConfiguration());
    } else {
        m_client.connectToHost();
    }
}

void MqttBackend::scheduleReconnect()
{
    if (m_started && !m_reconnectTimer.isActive()) {
        m_reconnectTimer.start();
    }
}
