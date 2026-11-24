#include "recovery-common.h"

#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDebug>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QPair>
#include <QRegularExpression>
#include <QTemporaryDir>

#include <algorithm>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <sys/file.h>
#include <sys/statvfs.h>
#include <unistd.h>

using namespace Recovery;

namespace {

constexpr quint64 kMinimumFreeBytes = 64ULL * 1024 * 1024;
const QString kRecoveryLabel = QStringLiteral("CUBE_RECOVERY");
const QString kComponentRoot = QStringLiteral("/usr/lib/cubelinux-recovery");
const QStringList kRequiredRuntimeFiles = {
    QStringLiteral("usr/lib/cubelinux-recovery/qml/InstallerError.qml"),
    QStringLiteral("usr/lib/cubelinux-recovery/qml/Main.qml"),
    QStringLiteral("usr/local/libexec/cubelinux/check-recovery-layout"),
    QStringLiteral("usr/local/libexec/cubelinux/cleanup-installed-fstab"),
    QStringLiteral("usr/local/libexec/cubelinux/factory-reset"),
    QStringLiteral("usr/local/libexec/cubelinux/install-bootc"),
    QStringLiteral("usr/local/libexec/cubelinux/install-recovery-boot"),
    QStringLiteral("usr/local/libexec/cubelinux/recovery-ui"),
    QStringLiteral("usr/local/libexec/cubelinux/verify-recovery-bundle"),
};

class UpdateLock {
public:
    UpdateLock()
    {
        m_descriptor = ::open("/run/cubelinux-recovery-update.lock", O_CREAT | O_WRONLY | O_CLOEXEC, 0644);
        ensure(m_descriptor >= 0, QStringLiteral("cannot open recovery update lock: %1")
                                      .arg(QString::fromLocal8Bit(std::strerror(errno))));
        if (::flock(m_descriptor, LOCK_EX | LOCK_NB) != 0) {
            const auto error = errno;
            ::close(m_descriptor);
            m_descriptor = -1;
            throw Failure(QStringLiteral("a recovery update is already running: %1")
                              .arg(QString::fromLocal8Bit(std::strerror(error))));
        }
    }

    UpdateLock(const UpdateLock &) = delete;
    UpdateLock &operator=(const UpdateLock &) = delete;

    ~UpdateLock()
    {
        if (m_descriptor >= 0) {
            ::flock(m_descriptor, LOCK_UN);
            ::close(m_descriptor);
        }
    }

private:
    int m_descriptor = -1;
};

quint64 availableBytes(const QString &path)
{
    struct statvfs info {};
    const auto encoded = QFile::encodeName(path);
    ensure(::statvfs(encoded.constData(), &info) == 0,
           QStringLiteral("could not measure free space at %1: %2")
               .arg(path, QString::fromLocal8Bit(std::strerror(errno))));
    return static_cast<quint64>(info.f_bavail) * static_cast<quint64>(info.f_frsize);
}

QStringList runtimeFileNames(const QString &root)
{
    const auto rootInfo = QFileInfo(root);
    ensure(rootInfo.isDir() && !rootInfo.isSymLink(),
           QStringLiteral("recovery runtime staging directory is missing or unsafe"));

    QStringList names;
    QDirIterator iterator(root, QDir::Files | QDir::NoDotAndDotDot | QDir::Hidden,
                          QDirIterator::Subdirectories);
    while (iterator.hasNext()) {
        const auto path = iterator.next();
        const QFileInfo info(path);
        ensure(info.isFile() && !info.isSymLink(),
               QStringLiteral("recovery runtime contains a symlink or non-file: %1").arg(path));
        const auto relative = QDir(root).relativeFilePath(path);
        ensure(relative.startsWith(QLatin1String("usr/lib/cubelinux-recovery/qml/")) ||
                   relative.startsWith(QLatin1String("usr/local/libexec/cubelinux/")),
               QStringLiteral("unexpected recovery runtime path: %1").arg(relative));
        ensure(QRegularExpression(QStringLiteral("^[A-Za-z0-9._/-]+$")).match(relative).hasMatch() &&
                   !relative.contains(QStringLiteral("..")),
               QStringLiteral("unsafe recovery runtime path: %1").arg(relative));
        if (relative.startsWith(QLatin1String("usr/local/libexec/cubelinux/"))) {
            ensure(info.isExecutable(), QStringLiteral("recovery helper is not executable: %1").arg(relative));
        }
        names.append(relative);
    }
    names.sort(Qt::CaseSensitive);
    for (const auto &required : kRequiredRuntimeFiles) {
        ensure(names.contains(required), QStringLiteral("recovery runtime is missing %1").arg(required));
    }
    return names;
}

QByteArray runtimeManifest(const QString &root)
{
    QByteArray manifest;
    for (const auto &name : runtimeFileNames(root)) {
        const auto path = root + QLatin1Char('/') + name;
        manifest += sha256File(path).toLatin1() + "  " + name.toUtf8() + '\n';
    }
    return manifest;
}

QByteArray componentManifest(const QString &componentRoot)
{
    QList<QPair<QString, QString>> files;
    const auto ui = componentRoot + QStringLiteral("/recovery-ui");
    ensure(QFileInfo(ui).isFile() && !isSymlink(ui),
           QStringLiteral("the compiled recovery interface is missing"));
    files.append({ui, QStringLiteral("usr/local/libexec/cubelinux/recovery-ui")});

    const auto qmlRoot = componentRoot + QStringLiteral("/qml");
    ensure(QFileInfo(qmlRoot).isDir() && !isSymlink(qmlRoot),
           QStringLiteral("the recovery QML directory is missing"));
    QDirIterator qmlIterator(qmlRoot, QDir::Files | QDir::NoDotAndDotDot | QDir::Hidden,
                             QDirIterator::Subdirectories);
    while (qmlIterator.hasNext()) {
        const auto source = qmlIterator.next();
        const QFileInfo info(source);
        ensure(info.isFile() && !info.isSymLink(),
               QStringLiteral("recovery QML contains a symlink or non-file: %1").arg(source));
        const auto relative = QDir(qmlRoot).relativeFilePath(source);
        files.append({source, QStringLiteral("usr/lib/cubelinux-recovery/qml/") + relative});
    }

    const auto runtimeRoot = componentRoot + QStringLiteral("/runtime");
    ensure(QFileInfo(runtimeRoot).isDir() && !isSymlink(runtimeRoot),
           QStringLiteral("the recovery helper directory is missing"));
    QDirIterator runtimeIterator(runtimeRoot, QDir::Files | QDir::NoDotAndDotDot | QDir::Hidden,
                                 QDirIterator::Subdirectories);
    while (runtimeIterator.hasNext()) {
        const auto source = runtimeIterator.next();
        const QFileInfo info(source);
        ensure(info.isFile() && !info.isSymLink(),
               QStringLiteral("recovery runtime contains a symlink or non-file: %1").arg(source));
        const auto relative = QDir(runtimeRoot).relativeFilePath(source);
        files.append({source, QStringLiteral("usr/local/libexec/cubelinux/") + relative});
    }

    std::sort(files.begin(), files.end(), [](const auto &left, const auto &right) {
        return left.second < right.second;
    });
    QByteArray manifest;
    QStringList names;
    for (const auto &file : files) {
        ensure(QRegularExpression(QStringLiteral("^[A-Za-z0-9._/-]+$")).match(file.second).hasMatch() &&
                   !file.second.contains(QStringLiteral("..")),
               QStringLiteral("unsafe recovery runtime path: %1").arg(file.second));
        if (file.second.startsWith(QLatin1String("usr/local/libexec/cubelinux/"))) {
            ensure(QFileInfo(file.first).isExecutable(),
                   QStringLiteral("recovery helper is not executable: %1").arg(file.second));
        }
        ensure(!names.contains(file.second), QStringLiteral("duplicate recovery runtime path: %1").arg(file.second));
        names.append(file.second);
        manifest += sha256File(file.first).toLatin1() + "  " + file.second.toUtf8() + '\n';
    }
    for (const auto &required : kRequiredRuntimeFiles) {
        ensure(names.contains(required), QStringLiteral("recovery component is missing %1").arg(required));
    }
    return manifest;
}

QByteArray runtimeMetadata(const QByteArray &manifest)
{
    const auto digest = QCryptographicHash::hash(manifest, QCryptographicHash::Sha256).toHex();
    return QByteArray("format=1\nmanifest_sha256=") + digest + '\n';
}

void writeText(const QString &path, const QByteArray &contents)
{
    ensure(!isSymlink(path), QStringLiteral("refusing to write through a symlink: %1").arg(path));
    QFile file(path);
    ensure(file.open(QIODevice::WriteOnly | QIODevice::Truncate),
           QStringLiteral("cannot write %1: %2").arg(path, file.errorString()));
    ensure(file.write(contents) == contents.size(),
           QStringLiteral("cannot write %1: %2").arg(path, file.errorString()));
    ensure(file.flush(), QStringLiteral("cannot flush %1: %2").arg(path, file.errorString()));
    ensure(::fsync(file.handle()) == 0,
           QStringLiteral("cannot sync %1: %2").arg(path, QString::fromLocal8Bit(std::strerror(errno))));
}

void copyRuntime(const QString &componentRoot, const QString &root)
{
    const auto qmlSource = componentRoot + QStringLiteral("/qml");
    const auto helpersSource = componentRoot + QStringLiteral("/runtime");
    const auto qmlTarget = root + QStringLiteral("/usr/lib/cubelinux-recovery/qml");
    const auto helpersTarget = root + QStringLiteral("/usr/local/libexec/cubelinux");
    ensure(QDir().mkpath(qmlTarget) && QDir().mkpath(helpersTarget),
           QStringLiteral("cannot create recovery runtime directories"));
    copyTreeOverlay(qmlSource, qmlTarget);
    copyTreeOverlay(helpersSource, helpersTarget);

    const auto uiSource = componentRoot + QStringLiteral("/recovery-ui");
    const auto uiTarget = helpersTarget + QStringLiteral("/recovery-ui");
    ensure(QFileInfo(uiSource).isFile() && !isSymlink(uiSource),
           QStringLiteral("the compiled recovery interface is missing"));
    copyFilePreservingDestination(uiSource, uiTarget);
    ensure(QFile::setPermissions(uiTarget, QFileDevice::ReadOwner | QFileDevice::WriteOwner |
                                             QFileDevice::ExeOwner | QFileDevice::ReadGroup |
                                             QFileDevice::ExeGroup | QFileDevice::ReadOther |
                                             QFileDevice::ExeOther),
           QStringLiteral("cannot set executable permissions on the recovery interface"));
}

QString buildRuntimeSlot(const QString &mount, const QString &inactive,
                         const QString &componentRoot)
{
    const auto runtimeDirectory = mount + QStringLiteral("/runtime");
    ensure(!isSymlink(runtimeDirectory) && QDir().mkpath(runtimeDirectory),
           QStringLiteral("cannot create recovery runtime directory"));
    const auto destination = runtimeDirectory + QLatin1Char('/') + inactive;
    const auto staged = runtimeDirectory + QStringLiteral("/.staging-") + inactive;
    ensure(!isSymlink(destination) && !isSymlink(staged),
           QStringLiteral("invalid recovery runtime slot path"));
    removeTree(staged);
    ensure(QDir().mkpath(staged), QStringLiteral("cannot create staged recovery runtime"));
    const auto root = staged + QStringLiteral("/rootfs");
    ensure(QDir().mkpath(root), QStringLiteral("cannot create staged recovery runtime root"));
    copyRuntime(componentRoot, root);

    const auto manifest = runtimeManifest(root);
    writeText(staged + QStringLiteral("/SHA256SUMS"), manifest);
    writeText(staged + QStringLiteral("/CUBELINUX_RECOVERY_RUNTIME"), runtimeMetadata(manifest));

    ensure(runtimeManifest(root) == manifest,
           QStringLiteral("staged recovery runtime verification failed"));
    const auto metadata = readFields(staged + QStringLiteral("/CUBELINUX_RECOVERY_RUNTIME"));
    ensure(metadata.size() == 2 && metadata.value(QStringLiteral("format")) == QLatin1String("1") &&
               metadata.value(QStringLiteral("manifest_sha256")) ==
                   QString::fromLatin1(QCryptographicHash::hash(manifest, QCryptographicHash::Sha256).toHex()),
           QStringLiteral("staged recovery runtime metadata is invalid"));

    run({QStringLiteral("/usr/bin/sync"), QStringLiteral("--file-system"), mount});

    removeTree(destination);
    const auto stagedEncoded = QFile::encodeName(staged);
    const auto destinationEncoded = QFile::encodeName(destination);
    ensure(::rename(stagedEncoded.constData(), destinationEncoded.constData()) == 0,
           QStringLiteral("cannot activate staged recovery runtime: %1")
               .arg(QString::fromLocal8Bit(std::strerror(errno))));
    syncDirectory(runtimeDirectory);
    return QString::fromLatin1(QCryptographicHash::hash(manifest, QCryptographicHash::Sha256).toHex());
}

void updateRuntime(const QString &mount, const QString &baseSlot, const QString &activeRuntime,
                   const Layout &layout, const QString &componentRoot)
{
    const auto selectedRuntime = activeRuntime.isEmpty() ? QStringLiteral("A") : activeRuntime;
    const auto currentDirectory = mount + QStringLiteral("/runtime/") + selectedRuntime;
    const auto expectedManifest = componentManifest(componentRoot);
    const auto expectedDigest = QString::fromLatin1(
        QCryptographicHash::hash(expectedManifest, QCryptographicHash::Sha256).toHex());

    if (!activeRuntime.isEmpty()) {
        try {
            const auto metadataPath = currentDirectory + QStringLiteral("/CUBELINUX_RECOVERY_RUNTIME");
            ensure(!isSymlink(metadataPath), QStringLiteral("recovery runtime metadata is a symlink"));
            const auto fields = readFields(metadataPath);
            if (fields.size() == 2 && fields.value(QStringLiteral("format")) == QLatin1String("1") &&
                fields.value(QStringLiteral("manifest_sha256")) == expectedDigest &&
                runtimeManifest(currentDirectory + QStringLiteral("/rootfs")) == expectedManifest) {
                qInfo("Recovery runtime already has the current component files.");
                return;
            }
        } catch (const std::exception &) {
            // A damaged active overlay can be replaced by staging into its peer slot.
        }
    }

    const auto inactive = selectedRuntime == QLatin1String("A") ? QStringLiteral("B") : QStringLiteral("A");
    // Estimate the runtime footprint from the exact destinations before staging.
    quint64 sourceBytes = static_cast<quint64>(expectedManifest.size());
    QDirIterator sourceIterator(componentRoot, QDir::Files | QDir::NoDotAndDotDot | QDir::Hidden,
                                QDirIterator::Subdirectories);
    while (sourceIterator.hasNext()) {
        const auto path = sourceIterator.next();
        const QFileInfo info(path);
        if (info.isSymLink() || !info.isFile()) {
            continue;
        }
        const auto relative = QDir(componentRoot).relativeFilePath(path);
        if (relative == QLatin1String("recovery-ui") || relative.startsWith(QLatin1String("qml/")) ||
            relative.startsWith(QLatin1String("runtime/"))) {
            sourceBytes += static_cast<quint64>(info.size());
        }
    }
    ensure(availableBytes(mount) >= sourceBytes + kMinimumFreeBytes,
           QStringLiteral("insufficient free space to stage the recovery runtime"));
    const auto digest = buildRuntimeSlot(mount, inactive, componentRoot);
    ensure(digest == expectedDigest, QStringLiteral("staged recovery runtime changed during update"));
    writeAtomically(mount + QStringLiteral("/active.cfg"),
                    recoveryConfig(baseSlot, layout.recoveryPartUuid, inactive).toUtf8());
    qInfo("Recovery runtime updated from the installed cubelinux component.");
}

void refreshRecoveryBootloader(const QString &componentRoot)
{
    const auto helper = componentRoot + QStringLiteral("/runtime/install-recovery-boot");
    ensure(QFileInfo(helper).isFile() && !isSymlink(helper),
           QStringLiteral("the signed recovery bootloader updater is missing"));
    run({helper, QStringLiteral("/")});
}

int updateRecovery()
{
    ensure(::geteuid() == 0, QStringLiteral("recovery updates require root"));
    UpdateLock lock;
    const auto componentRoot = kComponentRoot;
    const auto rootDevice = deviceInfo(systemRootSource());
    const auto rootId = blockId(rootDevice.partition, QStringLiteral("PARTUUID"));
    const auto diskId = blockId(rootDevice.disk, QStringLiteral("PTUUID"));
    const auto efiId = blockId(deviceSource(QStringLiteral("/boot/efi")), QStringLiteral("PARTUUID"));

    const auto result = runResult({QStringLiteral("/usr/sbin/blkid"), QStringLiteral("-t"),
                                   QStringLiteral("PARTLABEL=") + kRecoveryLabel,
                                   QStringLiteral("-o"), QStringLiteral("device")});
    ensure(result.normalExit && (result.exitCode == 0 || result.exitCode == 2),
           QStringLiteral("could not inspect recovery partitions"));

    QTemporaryDir temporary(QStringLiteral("/run/cubelinux-recovery-mount-XXXXXX"));
    ensure(temporary.isValid(), QStringLiteral("could not create recovery mount point"));
    const auto mountPath = temporary.path();
    QStringList matching;
    for (const auto &candidate : lines(result.standardOutput)) {
        if (deviceInfo(candidate).disk != rootDevice.disk) {
            continue;
        }
        const auto mounted = runResult({QStringLiteral("/usr/bin/findmnt"), QStringLiteral("--noheadings"),
                                        QStringLiteral("--source"), candidate});
        ensure(mounted.normalExit && (mounted.exitCode == 0 || mounted.exitCode == 1),
               QStringLiteral("could not determine whether recovery is mounted"));
        ensure(mounted.exitCode != 0, QStringLiteral("recovery partition is already mounted"));

        MountGuard mount(mountPath);
        mount.mount(candidate, QStringLiteral("ro,nodev,nosuid,noexec"));
        try {
            const auto slot = activeSlot(mountPath);
            const auto bundle = verifyBundle(mountPath + QStringLiteral("/slots/") + slot, true);
            const auto recoveryId = blockId(candidate, QStringLiteral("PARTUUID"));
            if (bundle.rootPartUuid.toLower() == rootId.toLower() &&
                bundle.diskPtUuid.toLower() == diskId.toLower() &&
                bundle.efiPartUuid.toLower() == efiId.toLower() &&
                bundle.recoveryPartUuid.toLower() == recoveryId.toLower()) {
                matching.append(candidate);
            }
            mount.unmount();
        } catch (...) {
            if (mount.mounted()) {
                mount.unmount();
            }
            throw;
        }
    }

    if (matching.isEmpty()) {
        qInfo("No recovery partition for this installation; skipping.");
        return 0;
    }
    ensure(matching.size() == 1, QStringLiteral("multiple recovery partitions match this system"));

    run({componentRoot + QStringLiteral("/recovery-ui"), QStringLiteral("--check-qml")}, 60000,
        {{QStringLiteral("QT_QPA_PLATFORM"), QStringLiteral("offscreen")},
         {QStringLiteral("QT_QUICK_BACKEND"), QStringLiteral("software")}});

    MountGuard mount(mountPath);
    mount.mount(matching.front(), QStringLiteral("rw,nodev,nosuid,noexec"));
    try {
        const auto baseSlot = activeSlot(mountPath);
        const auto layout = verifyBundle(mountPath + QStringLiteral("/slots/") + baseSlot, true);
        const auto activeRuntime = activeRuntimeSlot(mountPath);
        updateRuntime(mountPath, baseSlot, activeRuntime, layout, componentRoot);
        mount.unmount();
    } catch (...) {
        if (mount.mounted()) {
            mount.unmount();
        }
        throw;
    }

    refreshRecoveryBootloader(componentRoot);
    run({QStringLiteral("/usr/bin/systemctl"), QStringLiteral("start"),
         QStringLiteral("cubelinux-recovery-status.service")});
    return 0;
}

} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    if (app.arguments().size() != 1) {
        qCritical("Usage: cubelinux-recovery-update");
        return 2;
    }
    try {
        return updateRecovery();
    } catch (const std::exception &error) {
        qCritical().noquote() << "Recovery update failed:" << error.what();
        return 1;
    }
}
