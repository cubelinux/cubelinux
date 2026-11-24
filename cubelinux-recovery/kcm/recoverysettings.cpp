#include "recoverysettings.h"
#include <KPluginFactory>
#include <QFile>

K_PLUGIN_CLASS_WITH_JSON(RecoverySettings, "kcm_cubelinux_recovery.json")

RecoverySettings::RecoverySettings(QObject *parent, const KPluginMetaData &data)
    : KQuickConfigModule(parent, data)
{
    setButtons({});
    QFile statusFile(QStringLiteral("/run/cubelinux-recovery-status"));
    if (statusFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
        const auto status = QString::fromUtf8(statusFile.readAll());
        m_available = status.startsWith(QLatin1String("available\n"));
        if (!m_available) m_availabilityMessage = status.section(QLatin1Char('\n'), 1).trimmed();
    }
    if (!m_available && m_availabilityMessage.isEmpty())
        m_availabilityMessage = tr("Recovery is unavailable. A fresh installation is required to add it.");
    connect(&m_process, &QProcess::stateChanged, this, [this] { Q_EMIT busyChanged(); });
    connect(&m_process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        if (error == QProcess::FailedToStart) Q_EMIT restartFailed(m_process.errorString());
    });
    connect(&m_process, &QProcess::finished, this, [this](int code, QProcess::ExitStatus status) {
        if (code != 0 || status != QProcess::NormalExit) {
            const auto details = QString::fromUtf8(m_process.readAllStandardError()).trimmed();
            Q_EMIT restartFailed(details.isEmpty() ? tr("Could not restart into recovery.") : details);
        }
    });
}

bool RecoverySettings::busy() const { return m_process.state() != QProcess::NotRunning; }
bool RecoverySettings::available() const { return m_available; }
QString RecoverySettings::availabilityMessage() const { return m_availabilityMessage; }

void RecoverySettings::restartToRecovery()
{
    if (available() && !busy()) m_process.start(QStringLiteral("/usr/bin/pkexec"), {QStringLiteral("/usr/libexec/cubelinux-recovery-reboot")});
}

#include "recoverysettings.moc"
