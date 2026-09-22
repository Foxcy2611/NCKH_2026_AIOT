#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include "MqttHandler.h"

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QQmlApplicationEngine engine;

    MqttHandler mqttHandler;
    engine.rootContext()->setContextProperty("mqttHandler", &mqttHandler);

    const QUrl url(u"qrc:/Dashboard_DHT11/Main.qml"_qs);
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, []() { QCoreApplication::exit(-1); },
                     Qt::QueuedConnection);
    engine.load(url);

    return app.exec();
}