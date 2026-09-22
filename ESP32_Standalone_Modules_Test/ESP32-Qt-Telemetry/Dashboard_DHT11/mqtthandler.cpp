#include "MqttHandler.h"
#include <QSslConfiguration>
#include <QDebug>

MqttHandler::MqttHandler(QObject *parent) : QObject(parent) {
    m_client = new QMqttClient(this);

    m_client->setHostname("964dc275c0db4f789a75a75c92a78a33.s1.eu.hivemq.cloud");
    m_client->setPort(8883);
    m_client->setUsername("Test_DHT11");
    m_client->setPassword("NCKH_node_2026");

    connect(m_client, &QMqttClient::connected, this, &MqttHandler::onConnected);
    connect(m_client, &QMqttClient::messageReceived, this, &MqttHandler::onMessageReceived);
}

void MqttHandler::connectToBroker() {
    qDebug() << "Đang kết nối tới HiveMQ...";

    // Khởi tạo cấu hình SSL mặc định
    QSslConfiguration sslConfig = QSslConfiguration::defaultConfiguration();

    // Truyền cấu hình SSL thẳng vào hàm kết nối mã hóa
    m_client->connectToHostEncrypted(sslConfig);
}

void MqttHandler::onConnected() {
    qDebug() << "Đã kết nối tới HiveMQ Broker!";

    auto subscription = m_client->subscribe(QMqttTopicFilter("nckh/ngocchien/dht11"), 0);
    if (subscription) {
        qDebug() << "Subscribe thành công topic: nckh/ngocchien/dht11";
    }
}

void MqttHandler::onMessageReceived(const QByteArray &message, const QMqttTopicName &topic) {
    QJsonDocument doc = QJsonDocument::fromJson(message);
    if (doc.isObject()) {
        QJsonObject obj = doc.object();

        if (obj.contains("temp")) {
            m_temp = QString::number(obj["temp"].toDouble(), 'f', 1);
        }
        if (obj.contains("hum")) {
            m_hum = QString::number(obj["hum"].toDouble(), 'f', 1);
        }

        emit dataUpdated();
    }
}

QString MqttHandler::temperature() const { return m_temp; }
QString MqttHandler::humidity() const { return m_hum; }