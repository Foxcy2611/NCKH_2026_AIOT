#include <QGuiApplication>
#include <QCoreApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>

#include "DashboardData.h"
#include "MqttBackend.h"

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);

    // Custom dashboard controls use background/contentItem overrides.
    QQuickStyle::setStyle("Basic");

    DashboardData dashboardData;
    MqttBackend mqttBackend(&dashboardData);

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("dashboardBackend", &dashboardData);

    QObject::connect(
        &engine,
        &QQmlApplicationEngine::objectCreationFailed,
        &app,
        []() {
            QCoreApplication::exit(-1);
        },
        Qt::QueuedConnection
    );

    engine.loadFromModule(
        "Dashboard_Qt6",
        "Main"
    );

    const QString mqttConfigPath = QCoreApplication::applicationDirPath()
                                   + QStringLiteral("/mqtt_config.json");
    mqttBackend.start(mqttConfigPath);

    return app.exec();
}
