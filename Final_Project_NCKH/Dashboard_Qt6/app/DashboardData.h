#ifndef DASHBOARD_DATA_H
#define DASHBOARD_DATA_H

#include <QQmlPropertyMap>
#include <QString>

class DashboardData final : public QQmlPropertyMap
{
    Q_OBJECT

public:
    explicit DashboardData(QObject *parent = nullptr);

    bool applyCompletePacketJson(const QByteArray &json, QString *errorMessage = nullptr);
    void setTransportConnected(bool connected, const QString &status);

private:
    static QString operatingModeName(int value);
    static QString uplinkTypeName(int value);
    static QString eventTypeName(int value);
    static QString classificationName(int value);
    static QString audioQualityName(int value);
    static QString formatTimestamp(quint64 timestampMs, const QString &basis);

    void appendHistory(const QString &key, double value);
    void updateGoogleMap(double latitude, double longitude);

    QString m_googleMapsApiKey;
    QString m_lastPatientEventId;
};

#endif
