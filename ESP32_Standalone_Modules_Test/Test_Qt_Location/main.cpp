#include <QGuiApplication>
#include <QQmlApplicationEngine>

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);

    QQmlApplicationEngine engine;

    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, []() { QCoreApplication::exit(-1); },
                     Qt::QueuedConnection);

    // Qt 6 chuẩn sẽ gọi trực tiếp qua tên Module URI và tên file (không có đuôi .qml)
    engine.loadFromModule("Test_Qt_Location", "Main");

    return app.exec();
}