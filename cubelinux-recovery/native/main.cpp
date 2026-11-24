#include <QFile>
#include <QDir>
#include <QCommandLineOption>
#include <QCommandLineParser>
#include <QDebug>
#include <QGuiApplication>
#include <QProcess>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QStringList>

class RecoveryController : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool restarting READ restarting NOTIFY restartingChanged)
public:
    explicit RecoveryController(QObject *parent = nullptr) : QObject(parent) {
        process.setProcessChannelMode(QProcess::MergedChannels);
        process.setStandardOutputFile(QStringLiteral("/run/cubelinux-factory-reset.log"), QIODevice::Truncate);
        connect(&process, &QProcess::finished, this, [this](int code, QProcess::ExitStatus status) {
            if (reported) return;
            reported = true;
            const bool success = code == 0 && status == QProcess::NormalExit;
            Q_EMIT finished(success, success ? QString() : resetFailureMessage());
        });
        connect(&process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
            if (error == QProcess::FailedToStart && !reported) {
                reported = true;
                Q_EMIT finished(false, process.errorString());
            }
        });
        connect(&restartProcess, &QProcess::finished, this, [this](int code, QProcess::ExitStatus status) {
            if (restartReported || (code == 0 && status == QProcess::NormalExit)) return;
            restartReported = true;
            m_restarting = false;
            Q_EMIT restartingChanged();
            const auto details = QString::fromUtf8(restartProcess.readAllStandardError()).trimmed();
            Q_EMIT restartFailed(details.isEmpty() ? tr("Could not restart the computer.") : details);
        });
        connect(&restartProcess, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
            if (error == QProcess::FailedToStart && !restartReported) {
                restartReported = true;
                m_restarting = false;
                Q_EMIT restartingChanged();
                Q_EMIT restartFailed(restartProcess.errorString());
            }
        });
    }

    bool restarting() const { return m_restarting; }

    Q_INVOKABLE void startReset() {
        if (process.state() != QProcess::NotRunning) return;
        QFile cmdline(QStringLiteral("/proc/cmdline"));
        if (!cmdline.open(QIODevice::ReadOnly)) {
            Q_EMIT finished(false, tr("Could not identify the recovery environment."));
            return;
        }
        const auto tokens = QString::fromUtf8(cmdline.readAll()).split(QLatin1Char(' '), Qt::SkipEmptyParts);
        QStringList recoverySlots;
        for (const auto &token : tokens) {
            if (token.startsWith(QLatin1String("cubelinux.recovery_slot=")))
                recoverySlots.append(token.mid(int(sizeof("cubelinux.recovery_slot=") - 1)).trimmed());
        }
        if (recoverySlots.size() != 1 || (recoverySlots.first() != QLatin1String("A") && recoverySlots.first() != QLatin1String("B"))) {
            Q_EMIT finished(false, tr("The recovery slot could not be identified."));
            return;
        }
        reported = false;
        process.start(QStringLiteral("/usr/local/libexec/cubelinux/factory-reset"),
                      {QStringLiteral("/run/initramfs/live/slots/") + recoverySlots.first(),
                       QStringLiteral("--confirm-factory-reset")});
    }

    Q_INVOKABLE void restart() {
        if (m_restarting) return;
        restartReported = false;
        m_restarting = true;
        Q_EMIT restartingChanged();
        restartProcess.start(QStringLiteral("/usr/bin/systemctl"), {QStringLiteral("reboot")});
    }

Q_SIGNALS:
    void finished(bool success, const QString &message);
    void restartFailed(const QString &message);
    void restartingChanged();
private:
    QString resetFailureMessage() const {
        const QString path = QStringLiteral("/run/cubelinux-factory-reset.log");
        QFile log(path);
        if (!log.open(QIODevice::ReadOnly))
            return tr("The reset failed and its log could not be read.");
        constexpr qint64 displayLimit = 65536;
        const bool truncated = log.size() > displayLimit;
        if (truncated && !log.seek(log.size() - displayLimit))
            return tr("The reset failed. The log could not be read: %1").arg(path);
        const auto output = QString::fromUtf8(log.readAll()).trimmed();
        const auto heading = truncated
            ? tr("Showing the end of the log. Full log until reboot: %1").arg(path)
            : tr("Log available until reboot: %1").arg(path);
        return output.isEmpty() ? heading : heading + QStringLiteral("\n\n") + output;
    }

    QProcess process;
    QProcess restartProcess;
    bool reported = false;
    bool restartReported = false;
    bool m_restarting = false;
};

int main(int argc, char **argv) {
    QGuiApplication app(argc, argv);
    QCommandLineParser parser;
    parser.addOption(QCommandLineOption(QStringLiteral("check-qml"),
                                        QStringLiteral("Load both recovery screens and exit.")));
    parser.addOption(QCommandLineOption(QStringLiteral("installer-error"),
                                        QStringLiteral("Show the installer preflight error screen."),
                                        QStringLiteral("message")));
    if (!parser.parse(app.arguments())) {
        qCritical().noquote() << parser.errorText();
        return 2;
    }
    RecoveryController controller;
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty(QStringLiteral("recoveryController"), &controller);
    QString qmlFile = QStringLiteral("Main.qml");
    if (parser.isSet(QStringLiteral("installer-error"))) {
        engine.rootContext()->setContextProperty(QStringLiteral("installerErrorText"),
                                                 parser.value(QStringLiteral("installer-error")));
        qmlFile = QStringLiteral("InstallerError.qml");
    }
    const QString qmlDirectory = QStringLiteral("/usr/lib/cubelinux-recovery/qml");
    engine.load(QUrl::fromLocalFile(QDir(qmlDirectory).filePath(qmlFile)));
    if (engine.rootObjects().isEmpty()) return 1;
    if (parser.isSet(QStringLiteral("check-qml"))) {
        engine.rootContext()->setContextProperty(QStringLiteral("installerErrorText"), QStringLiteral("Preflight error"));
        engine.load(QUrl::fromLocalFile(QDir(qmlDirectory).filePath(QStringLiteral("InstallerError.qml"))));
        return engine.rootObjects().size() == 2 ? 0 : 1;
    }
    return app.exec();
}

#include "main.moc"
