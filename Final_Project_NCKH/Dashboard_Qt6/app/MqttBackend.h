#ifndef MQTT_BACKEND_H
#define MQTT_BACKEND_H

#include <QMqttClient>
#include <QObject>
#include <QTimer>

class DashboardData;

class MqttBackend final : public QObject
{
    Q_OBJECT

public:
    explicit MqttBackend(DashboardData *dashboardData, QObject *parent = nullptr);

    bool start(const QString &configPath);

private:
    struct Settings {
        QString host;
        quint16 port = 8883;
        QString username;
        QString password;
        QString topic;
        bool tls = true;
    };

    bool loadSettings(const QString &configPath, QString *errorMessage);
    void connectToBroker();
    void scheduleReconnect();

    DashboardData *m_dashboardData = nullptr;
    QMqttClient m_client;
    QTimer m_reconnectTimer;
    Settings m_settings;
    bool m_started = false;
};

#endif
