/*
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#include <Category/Category.h>
#include <Transaction/Transaction.h>
#include <resources/AbstractResourcesBackend.h>
#include <resources/StandardBackendUpdater.h>

#include <KLocalizedString>

#include <QDate>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QTimer>
#include <QUrl>

#include <functional>
#include <utility>

class BootcBackend;

class BootcResource final : public AbstractResource
{
    Q_OBJECT
public:
    explicit BootcResource(BootcBackend *backend);

    QString packageName() const override;
    QString name() const override;
    QString comment() override;
    QVariant icon() const override;
    bool canExecute() const override;
    void invokeApplication() const override;
    State state() override;
    bool hasCategory(const QString &category) const override;
    Type type() const override;
    quint64 size() override;
    QJsonArray licenses() override;
    QString installedVersion() const override;
    QString availableVersion() const override;
    QString longDescription() override;
    QString origin() const override;
    QString section() override;
    QString author() const override;
    QList<PackageState> addonsInformation() override;
    QString sourceIcon() const override;
    QDate releaseDate() const override;
    QUrl url() const override;
    QString appstreamId() const override;
    bool isRemovable() const override;
    void fetchChangelog() override;
    void fetchScreenshots() override;

    void setSystemState(QString image, QString version, QString digest, bool staged);
    void setUpdateAvailable(QString digest);
    void clearUpdateAvailable();

private:
    QString m_image;
    QString m_installedVersion;
    QString m_availableVersion;
    QString m_digest;
    bool m_staged = false;
    State m_state = Installed;
};

class BootcTransaction final : public Transaction
{
    Q_OBJECT
public:
    using Completion = std::function<void(bool, const QString &)>;

    BootcTransaction(QObject *parent, AbstractResource *resource, Completion completion)
        : Transaction(parent, resource, InstallRole)
        , m_process(new QProcess(this))
        , m_completion(std::move(completion))
    {
        setStatus(SetupStatus);
        setCancellable(true);
        connect(m_process, &QProcess::readyReadStandardOutput, this, [this] {
            m_process->readAllStandardOutput();
            setProgress(qMin(90, progress() + 5));
        });
        connect(m_process, &QProcess::readyReadStandardError, this, [this] {
            m_error += m_process->readAllStandardError();
            setProgress(qMin(90, progress() + 5));
        });
        connect(m_process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
            if (error == QProcess::FailedToStart) {
                finish(false, m_process->errorString());
            }
        });
        connect(m_process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this, [this](int code, QProcess::ExitStatus status) {
            const QString message = QString::fromLocal8Bit(m_error).trimmed();
            finish(status == QProcess::NormalExit && code == 0, message);
        });
    }

    void start()
    {
        setStatus(DownloadingStatus);
        setProgress(1);
        m_process->start(QStringLiteral("/usr/bin/pkexec"), {QStringLiteral("/usr/bin/bootc"), QStringLiteral("upgrade")});
    }

    void cancel() override
    {
        if (m_process->state() != QProcess::NotRunning) {
            m_process->terminate();
        }
    }

private:
    void finish(bool success, const QString &message)
    {
        if (m_finished) {
            return;
        }
        m_finished = true;
        setCancellable(false);
        if (success) {
            setProgress(100);
        }
        m_completion(success, message);
        setStatus(success ? DoneStatus : DoneWithErrorStatus);
    }

    QProcess *m_process;
    Completion m_completion;
    QByteArray m_error;
    bool m_finished = false;
};

class BootcBackend final : public AbstractResourcesBackend
{
    Q_OBJECT
public:
    explicit BootcBackend(QObject *parent = nullptr)
        : AbstractResourcesBackend(parent)
        , m_resource(new BootcResource(this))
        , m_updater(new StandardBackendUpdater(this))
    {
        connect(m_updater, &StandardBackendUpdater::updatesCountChanged, this, &AbstractResourcesBackend::updatesCountChanged);
        QTimer::singleShot(0, this, &BootcBackend::checkForUpdates);
    }

    bool isValid() const override
    {
        return QFileInfo::exists(QStringLiteral("/run/ostree-booted")) && QFileInfo(QStringLiteral("/usr/bin/bootc")).isExecutable()
            && QFileInfo(QStringLiteral("/usr/bin/skopeo")).isExecutable() && QFileInfo(QStringLiteral("/usr/bin/pkexec")).isExecutable();
    }

    int updatesCount() const override
    {
        return m_updater->updatesCount();
    }

    AbstractBackendUpdater *backendUpdater() const override
    {
        return m_updater;
    }

    AbstractReviewsBackend *reviewsBackend() const override
    {
        return nullptr;
    }

    ResultsStream *search(const Filters &filter) override
    {
        if (!m_resource || m_resource->state() < filter.state) {
            return new ResultsStream(QStringLiteral("bootc-empty"), {});
        }
        if (filter.category && filter.category->untranslatedName() != QLatin1String("Operating System")) {
            return new ResultsStream(QStringLiteral("bootc-empty"), {});
        }
        const QString term = filter.search.trimmed();
        if (!term.isEmpty() && !m_resource->name().contains(term, Qt::CaseInsensitive)
            && !m_resource->comment().contains(term, Qt::CaseInsensitive)
            && !m_resource->installedVersion().contains(term, Qt::CaseInsensitive)) {
            return new ResultsStream(QStringLiteral("bootc-empty"), {});
        }
        return new ResultsStream(QStringLiteral("bootc-system-image"), {m_resource});
    }

    Transaction *installApplication(AbstractResource *resource, const AddonList &) override
    {
        return installApplication(resource);
    }

    Transaction *installApplication(AbstractResource *resource) override
    {
        if (resource != m_resource || resource->state() != AbstractResource::Upgradeable || m_transactionRunning) {
            return nullptr;
        }
        m_transactionRunning = true;
        auto transaction = new BootcTransaction(this, resource, [this](bool success, const QString &message) {
            m_transactionRunning = false;
            if (success) {
                refreshStatus();
                if (m_staged) {
                    m_updater->setNeedsReboot(true);
                    m_resource->clearUpdateAvailable();
                } else {
                    Q_EMIT passiveMessage(i18n("bootc completed without staging an image update."));
                }
            } else if (!message.isEmpty()) {
                Q_EMIT passiveMessage(i18n("bootc upgrade failed: %1", message));
            }
            Q_EMIT contentsChanged();
            Q_EMIT fetchingUpdatesProgressChanged();
        });
        transaction->start();
        return transaction;
    }

    Transaction *removeApplication(AbstractResource *) override
    {
        return nullptr;
    }

    void checkForUpdates() override
    {
        if (m_checkProcess || m_transactionRunning) {
            return;
        }
        QString statusError;
        if (!refreshStatus(&statusError)) {
            Q_EMIT passiveMessage(i18n("Could not read bootc system status: %1", statusError));
            return;
        }
        if (m_staged) {
            m_updater->setNeedsReboot(true);
            m_resource->clearUpdateAvailable();
            Q_EMIT contentsChanged();
            return;
        }
        m_updater->setNeedsReboot(false);
        m_resource->clearUpdateAvailable();
        if (m_imageReference.isEmpty() || m_imageReference.contains(QLatin1Char('@'))) {
            Q_EMIT passiveMessage(i18n("This bootc image does not track a registry tag that can be checked for updates."));
            Q_EMIT contentsChanged();
            return;
        }

        QString transport = QStringLiteral("docker://");
        QString reference = m_imageReference;
        if (reference.startsWith(QStringLiteral("docker://"))) {
            transport.clear();
        } else if (reference.startsWith(QStringLiteral("ostree-remote:")) || reference.startsWith(QStringLiteral("containers-storage:"))) {
            Q_EMIT passiveMessage(i18n("Discover update checks support registry-backed bootc images."));
            Q_EMIT contentsChanged();
            return;
        }

        m_checkProcess = new QProcess(this);
        m_checkOutput.clear();
        connect(m_checkProcess, &QProcess::readyReadStandardOutput, this, [this] {
            m_checkOutput += m_checkProcess->readAllStandardOutput();
        });
        connect(m_checkProcess, &QProcess::readyReadStandardError, this, [this] {
            m_checkOutput += m_checkProcess->readAllStandardError();
        });
        connect(m_checkProcess, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this, [this](int code, QProcess::ExitStatus status) {
            const QByteArray output = m_checkOutput.trimmed();
            m_checkProcess->deleteLater();
            m_checkProcess = nullptr;
            if (status != QProcess::NormalExit || code != 0) {
                const QString error = QString::fromLocal8Bit(output).trimmed();
                if (!error.isEmpty()) {
                    Q_EMIT passiveMessage(i18n("Could not check for bootc updates: %1", error));
                }
            } else {
                const QString digest = QString::fromLocal8Bit(output).trimmed();
                if (!digest.isEmpty() && digest != m_currentDigest) {
                    m_resource->setUpdateAvailable(digest);
                }
            }
            Q_EMIT contentsChanged();
            Q_EMIT fetchingUpdatesProgressChanged();
        });
        connect(m_checkProcess, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
            if (error == QProcess::FailedToStart) {
                m_checkProcess->deleteLater();
                m_checkProcess = nullptr;
                Q_EMIT passiveMessage(i18n("Could not start skopeo to check the bootc image registry."));
                Q_EMIT contentsChanged();
                Q_EMIT fetchingUpdatesProgressChanged();
            }
        });
        Q_EMIT fetchingUpdatesProgressChanged();
        m_checkProcess->start(QStringLiteral("/usr/bin/skopeo"),
                              {QStringLiteral("inspect"), QStringLiteral("--format={{.Digest}}"), transport + reference});
    }

    QString displayName() const override
    {
        return QStringLiteral("bootc");
    }

    bool hasApplications() const override
    {
        return true;
    }

    int fetchingUpdatesProgress() const override
    {
        return m_checkProcess ? 0 : 100;
    }

private:
    bool refreshStatus(QString *errorMessage = nullptr)
    {
        QProcess process;
        process.start(QStringLiteral("/usr/bin/pkexec"),
                      {QStringLiteral("/usr/bin/bootc"), QStringLiteral("status"), QStringLiteral("--format=json"), QStringLiteral("--format-version=1")});
        if (!process.waitForStarted(2000)) {
            if (errorMessage) {
                *errorMessage = process.errorString();
            }
            return false;
        }
        if (!process.waitForFinished(10000) || process.exitStatus() != QProcess::NormalExit || process.exitCode() != 0) {
            if (errorMessage) {
                const QString details = QString::fromLocal8Bit(process.readAllStandardError()).trimmed();
                *errorMessage = details.isEmpty() ? process.errorString() : details;
            }
            return false;
        }
        QJsonParseError parseError;
        const auto document = QJsonDocument::fromJson(process.readAllStandardOutput(), &parseError);
        if (!document.isObject()) {
            if (errorMessage) {
                *errorMessage = i18n("bootc returned invalid JSON: %1", parseError.errorString());
            }
            return false;
        }
        const QJsonObject root = document.object();
        const QJsonObject status = root.value(QStringLiteral("status")).toObject();
        const QJsonObject booted = status.value(QStringLiteral("booted")).toObject();
        if (booted.isEmpty()) {
            if (errorMessage) {
                *errorMessage = i18n("bootc status did not include a booted deployment.");
            }
            return false;
        }
        const QJsonObject image = booted.value(QStringLiteral("image")).toObject();
        const QJsonObject specImage = root.value(QStringLiteral("spec")).toObject().value(QStringLiteral("image")).toObject();
        QJsonValue source = specImage.value(QStringLiteral("image"));
        if (source.isObject()) {
            source = source.toObject().value(QStringLiteral("image"));
        }
        if (source.toString().isEmpty()) {
            source = image.value(QStringLiteral("image"));
            if (source.isObject()) {
                source = source.toObject().value(QStringLiteral("image"));
            }
        }
        m_imageReference = source.toString();
        m_currentDigest = image.value(QStringLiteral("imageDigest")).toString();
        m_staged = !status.value(QStringLiteral("staged")).isNull() && !status.value(QStringLiteral("staged")).isUndefined();
        m_resource->setSystemState(m_imageReference,
                                  image.value(QStringLiteral("version")).toString(),
                                  m_currentDigest,
                                  m_staged);
        m_updater->setNeedsReboot(m_staged);
        return true;
    }

    BootcResource *m_resource;
    StandardBackendUpdater *m_updater;
    QProcess *m_checkProcess = nullptr;
    QByteArray m_checkOutput;
    QString m_imageReference;
    QString m_currentDigest;
    bool m_staged = false;
    bool m_transactionRunning = false;
};

BootcResource::BootcResource(BootcBackend *backend)
    : AbstractResource(backend)
{
}

QString BootcResource::packageName() const
{
    return QStringLiteral("bootc-system-image");
}

QString BootcResource::name() const
{
    return i18n("Operating system image");
}

QString BootcResource::comment()
{
    if (m_staged) {
        return i18n("Update staged; restart to use it");
    }
    return m_state == Upgradeable ? i18n("A newer bootc image is available") : i18n("Bootc system image");
}

QVariant BootcResource::icon() const
{
    return QStringLiteral("system-software-update");
}

bool BootcResource::canExecute() const
{
    return false;
}

void BootcResource::invokeApplication() const
{
}

AbstractResource::State BootcResource::state()
{
    return m_state;
}

bool BootcResource::hasCategory(const QString &category) const
{
    return category == QLatin1String("Operating System");
}

AbstractResource::Type BootcResource::type() const
{
    return System;
}

quint64 BootcResource::size()
{
    return 0;
}

QJsonArray BootcResource::licenses()
{
    return {};
}

QString BootcResource::installedVersion() const
{
    return m_installedVersion;
}

QString BootcResource::availableVersion() const
{
    return m_availableVersion;
}

QString BootcResource::longDescription()
{
    QString description = i18n("The operating system is delivered as a bootable container image.");
    if (!m_image.isEmpty()) {
        description += QStringLiteral("\n\n") + i18n("Image: %1", m_image);
    }
    if (!m_digest.isEmpty()) {
        description += QStringLiteral("\n") + i18n("Current image digest: %1", m_digest);
    }
    if (m_staged) {
        description += QStringLiteral("\n\n") + i18n("The staged image will be used after restarting the system.");
    }
    return description;
}

QString BootcResource::origin() const
{
    return QStringLiteral("bootc");
}

QString BootcResource::section()
{
    return i18n("Operating System");
}

QString BootcResource::author() const
{
    return QStringLiteral("bootc");
}

QList<PackageState> BootcResource::addonsInformation()
{
    return {};
}

QString BootcResource::sourceIcon() const
{
    return QStringLiteral("computer");
}

QDate BootcResource::releaseDate() const
{
    return {};
}

QUrl BootcResource::url() const
{
    return QUrl(QStringLiteral("bootc://system"));
}

QString BootcResource::appstreamId() const
{
    return QStringLiteral("org.containers.bootc.system");
}

bool BootcResource::isRemovable() const
{
    return false;
}

void BootcResource::fetchChangelog()
{
    Q_EMIT changelogFetched(longDescription());
}

void BootcResource::fetchScreenshots()
{
    Q_EMIT screenshotsFetched(Screenshots{});
}

void BootcResource::setSystemState(QString image, QString version, QString digest, bool staged)
{
    m_image = std::move(image);
    m_installedVersion = std::move(version);
    m_digest = std::move(digest);
    m_staged = staged;
    if (m_state != Upgradeable) {
        m_state = Installed;
    }
    Q_EMIT stateChanged();
}

void BootcResource::setUpdateAvailable(QString digest)
{
    m_availableVersion = digest;
    m_state = Upgradeable;
    Q_EMIT stateChanged();
}

void BootcResource::clearUpdateAvailable()
{
    m_availableVersion.clear();
    m_state = Installed;
    Q_EMIT stateChanged();
}

DISCOVER_BACKEND_PLUGIN(BootcBackend)

#include "BootcBackend.moc"
