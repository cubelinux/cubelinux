#include "recovery-common.h"

#include <QCryptographicHash>
#include <QDebug>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QProcess>
#include <QProcessEnvironment>
#include <QRegularExpression>
#include <QSet>
#include <QSaveFile>

#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <utility>

namespace Recovery {

namespace {

QString commandDescription(const QStringList &arguments)
{
    return arguments.join(QLatin1Char(' '));
}

QStringList requiredBundleFiles()
{
    return {
        QStringLiteral("LiveOS/squashfs.img"),
        QStringLiteral("boot/vmlinuz"),
        QStringLiteral("boot/initrd.img"),
        QStringLiteral("CUBELINUX_IMAGE_REF"),
        QStringLiteral("CUBELINUX_LAYOUT"),
    };
}

} // namespace

Failure::Failure(const QString &message)
    : std::runtime_error(message.toUtf8().constData())
{
}

void ensure(bool condition, const QString &message)
{
    if (!condition) {
        throw Failure(message);
    }
}

ProcessResult runResult(const QStringList &arguments, int timeoutMs,
                        const QMap<QString, QString> &environment)
{
    ensure(!arguments.isEmpty(), QStringLiteral("cannot run an empty command"));

    QProcess process;
    if (!environment.isEmpty()) {
        auto processEnvironment = QProcessEnvironment::systemEnvironment();
        for (auto iterator = environment.cbegin(); iterator != environment.cend(); ++iterator) {
            processEnvironment.insert(iterator.key(), iterator.value());
        }
        process.setProcessEnvironment(processEnvironment);
    }
    process.setProgram(arguments.front());
    process.setArguments(arguments.mid(1));
    process.start();
    if (!process.waitForStarted()) {
        throw Failure(QStringLiteral("could not start %1: %2")
                          .arg(commandDescription(arguments), process.errorString()));
    }
    if (!process.waitForFinished(timeoutMs)) {
        process.kill();
        process.waitForFinished();
        throw Failure(QStringLiteral("command timed out: %1")
                          .arg(commandDescription(arguments)));
    }

    ProcessResult result;
    result.exitCode = process.exitCode();
    result.normalExit = process.exitStatus() == QProcess::NormalExit;
    result.standardOutput = QString::fromLocal8Bit(process.readAllStandardOutput()).trimmed();
    result.standardError = QString::fromLocal8Bit(process.readAllStandardError()).trimmed();
    return result;
}

QString run(const QStringList &arguments, int timeoutMs,
            const QMap<QString, QString> &environment)
{
    const auto result = runResult(arguments, timeoutMs, environment);
    if (!result.normalExit || result.exitCode != 0) {
        auto detail = result.standardError;
        if (detail.isEmpty()) {
            detail = result.standardOutput;
        }
        if (detail.isEmpty()) {
            detail = QStringLiteral("exit status %1").arg(result.exitCode);
        }
        throw Failure(QStringLiteral("%1: %2").arg(commandDescription(arguments), detail));
    }
    return result.standardOutput;
}

QStringList lines(const QString &text)
{
    QStringList result;
    for (const auto &line : text.split(QLatin1Char('\n'), Qt::SkipEmptyParts)) {
        const auto trimmed = line.trimmed();
        if (!trimmed.isEmpty()) {
            result.append(trimmed);
        }
    }
    return result;
}

QString deviceSource(const QString &mountPoint)
{
    return run({QStringLiteral("/usr/bin/findmnt"), QStringLiteral("-nro"),
                QStringLiteral("SOURCE"), QStringLiteral("--mountpoint"), mountPoint})
        .section(QLatin1Char('['), 0, 0);
}

QString systemRootSource()
{
    const auto sysroot = runResult({QStringLiteral("/usr/bin/findmnt"), QStringLiteral("-nro"),
                                    QStringLiteral("SOURCE"), QStringLiteral("--mountpoint"),
                                    QStringLiteral("/sysroot")});
    if (sysroot.normalExit && sysroot.exitCode == 0 && !sysroot.standardOutput.isEmpty()) {
        return sysroot.standardOutput.section(QLatin1Char('['), 0, 0);
    }
    return deviceSource(QStringLiteral("/"));
}

DeviceInfo deviceInfo(const QString &device)
{
    const auto output = run({QStringLiteral("/usr/bin/lsblk"), QStringLiteral("--inverse"),
                             QStringLiteral("--list"), QStringLiteral("--noheadings"),
                             QStringLiteral("--paths"), QStringLiteral("--output"),
                             QStringLiteral("NAME,TYPE"), QStringLiteral("--"), device});
    DeviceInfo result;
    for (const auto &line : lines(output)) {
        const auto fields = line.split(QRegularExpression(QStringLiteral("\\s+")), Qt::SkipEmptyParts);
        if (fields.size() != 2) {
            continue;
        }
        if (fields[1] == QLatin1String("part") && result.partition.isEmpty()) {
            result.partition = fields[0];
        }
        if (fields[1] == QLatin1String("disk") && result.disk.isEmpty()) {
            result.disk = fields[0];
        }
    }
    ensure(!result.partition.isEmpty() && !result.disk.isEmpty(),
           QStringLiteral("cannot identify the installed system disk"));
    return result;
}

QString efiPartitionForDisk(const QString &disk)
{
    const auto output = run({QStringLiteral("/usr/bin/lsblk"), QStringLiteral("--list"),
                             QStringLiteral("--noheadings"), QStringLiteral("--paths"),
                             QStringLiteral("--output"), QStringLiteral("NAME,PARTTYPE"),
                             QStringLiteral("--"), disk});
    QStringList matches;
    for (const auto &line : lines(output)) {
        const auto fields = line.split(QRegularExpression(QStringLiteral("\\s+")), Qt::SkipEmptyParts);
        if (fields.size() == 2 &&
            fields[1].compare(QStringLiteral("c12a7328-f81f-11d2-ba4b-00a0c93ec93b"), Qt::CaseInsensitive) == 0) {
            matches.append(fields[0]);
        }
    }
    ensure(matches.size() == 1,
           QStringLiteral("expected one EFI System Partition on %1, found %2")
               .arg(disk).arg(matches.size()));
    ensure(deviceInfo(matches.front()).disk == disk,
           QStringLiteral("EFI System Partition is not on the installed system disk"));
    ensure(blockId(matches.front(), QStringLiteral("TYPE")) == QLatin1String("vfat"),
           QStringLiteral("EFI System Partition is not FAT formatted"));
    return matches.front();
}

QString blockId(const QString &device, const QString &tag)
{
    return run({QStringLiteral("/usr/sbin/blkid"), QStringLiteral("-s"), tag,
                QStringLiteral("-o"), QStringLiteral("value"), device});
}

QString sha256File(const QString &path)
{
    QFile file(path);
    ensure(file.open(QIODevice::ReadOnly), QStringLiteral("cannot read %1: %2").arg(path, file.errorString()));
    QCryptographicHash hash(QCryptographicHash::Sha256);
    while (!file.atEnd()) {
        const auto chunk = file.read(1024 * 1024);
        ensure(!chunk.isEmpty() || file.atEnd(), QStringLiteral("cannot read %1: %2").arg(path, file.errorString()));
        hash.addData(chunk);
    }
    return QString::fromLatin1(hash.result().toHex());
}

QMap<QString, QString> readFields(const QString &path)
{
    QFile file(path);
    ensure(file.open(QIODevice::ReadOnly | QIODevice::Text),
           QStringLiteral("cannot read %1: %2").arg(path, file.errorString()));
    QMap<QString, QString> fields;
    while (!file.atEnd()) {
        const auto line = QString::fromUtf8(file.readLine()).trimmed();
        if (line.isEmpty()) {
            continue;
        }
        const auto separator = line.indexOf(QLatin1Char('='));
        ensure(separator > 0 && separator < line.size() - 1,
               QStringLiteral("invalid metadata in %1").arg(path));
        const auto key = line.left(separator);
        const auto value = line.mid(separator + 1);
        ensure(!fields.contains(key), QStringLiteral("duplicate metadata field in %1").arg(path));
        fields.insert(key, value);
    }
    return fields;
}

bool isUuid(const QString &value)
{
    static const QRegularExpression uuid(
        QStringLiteral("^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$"));
    return uuid.match(value).hasMatch();
}

Layout parseLayout(const QString &path)
{
    const auto fields = readFields(path);
    const QSet<QString> expected = {
        QStringLiteral("format"), QStringLiteral("disk_ptuuid"),
        QStringLiteral("root_partuuid"), QStringLiteral("recovery_partuuid"),
        QStringLiteral("efi_partuuid")};
    QSet<QString> actual;
    for (auto iterator = fields.cbegin(); iterator != fields.cend(); ++iterator) {
        actual.insert(iterator.key());
    }
    ensure(actual == expected &&
               fields.value(QStringLiteral("format")) == QLatin1String("1"),
           QStringLiteral("unsupported recovery layout"));
    for (const auto &key : expected) {
        if (key != QLatin1String("format")) {
            ensure(isUuid(fields.value(key)), QStringLiteral("invalid partition identifier in recovery layout"));
        }
    }
    return {fields.value(QStringLiteral("disk_ptuuid")), fields.value(QStringLiteral("root_partuuid")),
            fields.value(QStringLiteral("recovery_partuuid")), fields.value(QStringLiteral("efi_partuuid"))};
}

bool isSymlink(const QString &path)
{
    struct stat info {};
    if (::lstat(QFile::encodeName(path).constData(), &info) != 0) {
        return false;
    }
    return S_ISLNK(info.st_mode);
}

Layout verifyBundle(const QString &slot, bool checkContents)
{
    const auto manifestPath = slot + QStringLiteral("/SHA256SUMS");
    ensure(!isSymlink(manifestPath), QStringLiteral("recovery checksum manifest is a symlink"));
    QFile manifest(manifestPath);
    ensure(manifest.open(QIODevice::ReadOnly | QIODevice::Text),
           QStringLiteral("recovery checksum manifest is missing"));

    static const QRegularExpression checksumLine(QStringLiteral("^([0-9a-f]{64})  (.+)$"));
    QMap<QString, QString> checksums;
    while (!manifest.atEnd()) {
        const auto line = QString::fromUtf8(manifest.readLine()).trimmed();
        const auto match = checksumLine.match(line);
        ensure(match.hasMatch() && !checksums.contains(match.captured(2)),
               QStringLiteral("recovery checksum manifest is invalid"));
        checksums.insert(match.captured(2), match.captured(1));
    }

    QSet<QString> expected;
    for (const auto &name : requiredBundleFiles()) {
        expected.insert(name);
    }
    const auto digestPath = slot + QStringLiteral("/CUBELINUX_DIGEST");
    if (QFileInfo::exists(digestPath) || isSymlink(digestPath)) {
        expected.insert(QStringLiteral("CUBELINUX_DIGEST"));
    }
    QSet<QString> checksumNames;
    for (auto iterator = checksums.cbegin(); iterator != checksums.cend(); ++iterator) {
        checksumNames.insert(iterator.key());
    }
    ensure(checksumNames == expected,
           QStringLiteral("unexpected recovery checksum entries"));

    for (auto iterator = checksums.cbegin(); iterator != checksums.cend(); ++iterator) {
        const auto path = slot + QLatin1Char('/') + iterator.key();
        const QFileInfo info(path);
        ensure(!isSymlink(path) && info.isFile() && info.size() > 0,
               QStringLiteral("recovery file is missing or invalid: %1").arg(iterator.key()));
        if (checkContents) {
            ensure(sha256File(path) == iterator.value(),
                   QStringLiteral("recovery checksum failed: %1").arg(iterator.key()));
        }
    }
    if (expected.contains(QStringLiteral("CUBELINUX_DIGEST"))) {
        QFile digestFile(digestPath);
        ensure(digestFile.open(QIODevice::ReadOnly | QIODevice::Text),
               QStringLiteral("recovery image digest is invalid"));
        static const QRegularExpression digestPattern(QStringLiteral("^sha256:[0-9a-f]{64}\\n?$"));
        ensure(digestPattern.match(QString::fromLatin1(digestFile.readAll())).hasMatch(),
               QStringLiteral("recovery image digest is invalid"));
    }
    return parseLayout(slot + QStringLiteral("/CUBELINUX_LAYOUT"));
}

QString activeSlot(const QString &mount)
{
    QFile file(mount + QStringLiteral("/active.cfg"));
    ensure(file.open(QIODevice::ReadOnly | QIODevice::Text), QStringLiteral("recovery slot selector is missing"));
    static const QRegularExpression selector(QStringLiteral("^set recovery_slot=([AB])$"));
    QString selected;
    int matches = 0;
    while (!file.atEnd()) {
        const auto match = selector.match(QString::fromUtf8(file.readLine()).trimmed());
        if (match.hasMatch()) {
            selected = match.captured(1);
            ++matches;
        }
    }
    ensure(matches == 1, QStringLiteral("invalid recovery slot selector"));
    return selected;
}

QString activeRuntimeSlot(const QString &mount)
{
    QFile file(mount + QStringLiteral("/active.cfg"));
    ensure(file.open(QIODevice::ReadOnly | QIODevice::Text), QStringLiteral("recovery slot selector is missing"));
    static const QRegularExpression selector(QStringLiteral("^set recovery_runtime_slot=([AB])$"));
    QString selected;
    int matches = 0;
    while (!file.atEnd()) {
        const auto line = QString::fromUtf8(file.readLine()).trimmed();
        if (!line.startsWith(QLatin1String("set recovery_runtime_slot="))) {
            continue;
        }
        const auto match = selector.match(line);
        ensure(match.hasMatch(), QStringLiteral("invalid recovery runtime slot selector"));
        selected = match.captured(1);
        ++matches;
    }
    ensure(matches <= 1, QStringLiteral("duplicate recovery runtime slot selector"));
    return selected;
}

QString recoveryConfig(const QString &slot, const QString &recoveryId,
                       const QString &runtimeSlot)
{
    ensure((slot == QLatin1String("A") || slot == QLatin1String("B")) && isUuid(recoveryId),
           QStringLiteral("invalid recovery activation target"));
    ensure(runtimeSlot.isEmpty() || runtimeSlot == QLatin1String("A") || runtimeSlot == QLatin1String("B"),
           QStringLiteral("invalid recovery runtime activation target"));

    QString config = QStringLiteral("set recovery_slot=%1\n").arg(slot);
    if (!runtimeSlot.isEmpty()) {
        config += QStringLiteral("set recovery_runtime_slot=%1\n").arg(runtimeSlot);
    }
    config += QStringLiteral(
                  "linux ($recovery)/slots/%1/boot/vmlinuz root=live:PARTUUID=%2 ro "
                  "rd.live.image rd.live.dir=/slots/%1/LiveOS rd.live.overlay.overlayfs=1 "
                  "cubelinux.recovery=1 cubelinux.recovery_slot=%1")
                  .arg(slot, recoveryId);
    if (!runtimeSlot.isEmpty()) {
        config += QStringLiteral(" cubelinux.recovery_runtime_slot=%1").arg(runtimeSlot);
    }
    config += QStringLiteral(" console=tty0\ninitrd ($recovery)/slots/%1/boot/initrd.img\nboot\n").arg(slot);
    return config;
}

void writeAtomically(const QString &path, const QByteArray &contents, unsigned int mode)
{
    QSaveFile file(path);
    file.setDirectWriteFallback(false);
    ensure(file.open(QIODevice::WriteOnly), QStringLiteral("cannot create %1: %2").arg(path, file.errorString()));
    ensure(file.write(contents) == contents.size(), QStringLiteral("cannot write %1: %2").arg(path, file.errorString()));
    ensure(::fchmod(file.handle(), static_cast<mode_t>(mode)) == 0,
           QStringLiteral("cannot set permissions on %1: %2").arg(path, QString::fromLocal8Bit(std::strerror(errno))));
    ensure(::fsync(file.handle()) == 0,
           QStringLiteral("cannot sync %1: %2").arg(path, QString::fromLocal8Bit(std::strerror(errno))));
    ensure(file.commit(), QStringLiteral("cannot commit %1: %2").arg(path, file.errorString()));
    syncDirectory(QFileInfo(path).absolutePath());
}

void syncDirectory(const QString &path)
{
    const auto encoded = QFile::encodeName(path);
    const int descriptor = ::open(encoded.constData(), O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    ensure(descriptor >= 0, QStringLiteral("cannot open directory for sync %1: %2")
                                .arg(path, QString::fromLocal8Bit(std::strerror(errno))));
    const int result = ::fsync(descriptor);
    const int error = errno;
    ::close(descriptor);
    ensure(result == 0, QStringLiteral("cannot sync directory %1: %2")
                            .arg(path, QString::fromLocal8Bit(std::strerror(error))));
}

void copyFilePreservingDestination(const QString &source, const QString &destination)
{
    ensure(!isSymlink(source) && !isSymlink(destination), QStringLiteral("refusing to copy through a symlink"));
    QFile input(source);
    ensure(input.open(QIODevice::ReadOnly), QStringLiteral("cannot read %1: %2").arg(source, input.errorString()));
    QFile output(destination);
    ensure(output.open(QIODevice::WriteOnly | QIODevice::Truncate),
           QStringLiteral("cannot write %1: %2").arg(destination, output.errorString()));
    while (!input.atEnd()) {
        const auto chunk = input.read(1024 * 1024);
        ensure(!chunk.isEmpty() || input.atEnd(), QStringLiteral("cannot read %1: %2").arg(source, input.errorString()));
        ensure(output.write(chunk) == chunk.size(),
               QStringLiteral("cannot write %1: %2").arg(destination, output.errorString()));
    }
    ensure(output.flush(), QStringLiteral("cannot flush %1: %2").arg(destination, output.errorString()));
    ensure(::fsync(output.handle()) == 0,
           QStringLiteral("cannot sync %1: %2").arg(destination, QString::fromLocal8Bit(std::strerror(errno))));
}

void copyTreeOverlay(const QString &source, const QString &destination)
{
    const QFileInfo sourceInfo(source);
    ensure(sourceInfo.isDir() && !sourceInfo.isSymLink(), QStringLiteral("invalid recovery component directory"));
    ensure(QDir().mkpath(destination), QStringLiteral("cannot create %1").arg(destination));

    QDir sourceDir(source);
    const auto entries = sourceDir.entryInfoList(QDir::AllEntries | QDir::NoDotAndDotDot,
                                                  QDir::Name | QDir::DirsFirst);
    for (const auto &entry : entries) {
        const auto from = entry.absoluteFilePath();
        const auto to = destination + QLatin1Char('/') + entry.fileName();
        ensure(!entry.isSymLink(), QStringLiteral("recovery component contains a symlink: %1").arg(from));
        if (entry.isDir()) {
            ensure(!isSymlink(to) && (!QFileInfo(to).exists() || QFileInfo(to).isDir()),
                   QStringLiteral("recovery component path conflicts at %1").arg(to));
            ensure(QDir().mkpath(to), QStringLiteral("cannot create %1").arg(to));
            copyTreeOverlay(from, to);
            continue;
        }
        ensure(entry.isFile(), QStringLiteral("recovery component contains an unsupported file: %1").arg(from));
        const QFileInfo targetInfo(to);
        ensure(!targetInfo.exists() || targetInfo.isFile(), QStringLiteral("recovery component path conflicts at %1").arg(to));
        copyFilePreservingDestination(from, to);
        ensure(QFile::setPermissions(to, entry.permissions()),
               QStringLiteral("cannot set permissions on %1").arg(to));
    }
}

void removeTree(const QString &path)
{
    if (!QFileInfo::exists(path) && !isSymlink(path)) {
        return;
    }
    ensure(!isSymlink(path), QStringLiteral("refusing to remove a symlink: %1").arg(path));
    const QFileInfo info(path);
    if (info.isDir()) {
        ensure(QDir(path).removeRecursively(), QStringLiteral("cannot remove directory: %1").arg(path));
    } else {
        ensure(QFile::remove(path), QStringLiteral("cannot remove file: %1").arg(path));
    }
}

MountGuard::MountGuard(QString target)
    : m_target(std::move(target))
{
}

MountGuard::~MountGuard()
{
    if (m_mounted) {
        try {
            run({QStringLiteral("/usr/bin/umount"), m_target});
        } catch (...) {
        }
    }
}

void MountGuard::mount(const QString &device, const QString &options)
{
    ensure(!m_mounted, QStringLiteral("mount point is already in use"));
    run({QStringLiteral("/usr/bin/mount"), QStringLiteral("-o"), options, device, m_target});
    m_mounted = true;
}

void MountGuard::unmount()
{
    if (!m_mounted) {
        return;
    }
    run({QStringLiteral("/usr/bin/umount"), m_target});
    m_mounted = false;
}

bool MountGuard::mounted() const
{
    return m_mounted;
}

} // namespace Recovery
