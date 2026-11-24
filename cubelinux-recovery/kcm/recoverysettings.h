#pragma once
#include <KQuickConfigModule>
#include <QProcess>

class RecoverySettings : public KQuickConfigModule
{
    Q_OBJECT
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(bool available READ available CONSTANT)
    Q_PROPERTY(QString availabilityMessage READ availabilityMessage CONSTANT)
public:
    RecoverySettings(QObject *parent, const KPluginMetaData &data);
    bool busy() const;
    bool available() const;
    QString availabilityMessage() const;
    Q_INVOKABLE void restartToRecovery();
Q_SIGNALS:
    void busyChanged();
    void restartFailed(const QString &message);
private:
    QProcess m_process;
    bool m_available = false;
    QString m_availabilityMessage;
};
