#ifndef MQTTHANDLER_H
#define MQTTHANDLER_H

#include <QObject>
#include <QtMqtt/QMqttClient>
#include <QJsonDocument>
#include <QJsonObject>

class MqttHandler : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString temperature READ temperature NOTIFY dataUpdated)
    Q_PROPERTY(QString humidity READ humidity NOTIFY dataUpdated)

public:
    explicit MqttHandler(QObject *parent = nullptr);

    Q_INVOKABLE void connectToBroker();

    QString temperature() const;
    QString humidity() const;

signals:
    void dataUpdated();

private slots:
    void onConnected();
    void onMessageReceived(const QByteArray &message, const QMqttTopicName &topic);

private:
    QMqttClient *m_client;
    QString m_temp = "--";
    QString m_hum = "--";
};

#endif // MQTTHANDLER_H