#include "recovery-common.h"

#include <QCoreApplication>
#include <QDebug>
#include <QFile>
#include <QFileInfo>
#include <QRegularExpression>
#include <QSet>
#include <QTemporaryDir>

#include <unistd.h>

using namespace Recovery;

namespace {

const QString kRecoveryLabel = QStringLiteral("CUBE_RECOVERY");
const QString kSecureBootVariable = QStringLiteral(
    "/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c");
const QString kBootDirectory = QStringLiteral("/boot/efi/EFI/cubelinux-recovery");

QString lowercase(QString value)
{
    return value.toLower();
}

QSet<QString> keySet(const QMap<QString, QString> &fields)
{
    QSet<QString> keys;
    for (auto iterator = fields.cbegin(); iterator != fields.cend(); ++iterator) {
        keys.insert(iterator.key());
    }
    return keys;
}

bool hasExactKeys(const QMap<QString, QString> &fields, const QSet<QString> &expected)
{
    return keySet(fields) == expected;
}

void verifyFileDigest(const QString &path, const QString &expected, const QString &description)
{
    ensure(QFileInfo(path).isFile() && !isSymlink(path),
           QStringLiteral("The recovery boot file is missing: %1").arg(description));
    ensure(sha256File(path) == expected,
           QStringLiteral("The recovery boot file is damaged: %1").arg(description));
}

bool recoveryPartitionPresent(const QString &efiId, const QString &expectedRecoveryId,
                              const QString &expectedFsUuid, bool checkContents)
{
    const auto root = systemRootSource();
    const auto rootDevice = deviceInfo(root);
    const auto rootId = blockId(rootDevice.partition, QStringLiteral("PARTUUID"));
    const auto rootDiskId = blockId(rootDevice.disk, QStringLiteral("PTUUID"));
    const auto rootType = blockId(rootDevice.partition, QStringLiteral("TYPE"));
    ensure(rootType != QLatin1String("crypto_LUKS"),
           QStringLiteral("Factory reset is not yet available for encrypted installations."));
    ensure(rootType == QLatin1String("ext4"),
           QStringLiteral("The installed root filesystem is not supported by factory reset."));

    const auto efiSource = deviceSource(QStringLiteral("/boot/efi"));
    ensure(deviceInfo(efiSource).disk == rootDevice.disk,
           QStringLiteral("The EFI and root partitions are on different disks."));
    ensure(blockId(efiSource, QStringLiteral("TYPE")) == QLatin1String("vfat"),
           QStringLiteral("The EFI partition is not FAT formatted."));

    const auto result = runResult({QStringLiteral("/usr/sbin/blkid"), QStringLiteral("-t"),
                                   QStringLiteral("PARTLABEL=") + kRecoveryLabel,
                                   QStringLiteral("-o"), QStringLiteral("device")});
    ensure(result.normalExit && (result.exitCode == 0 || result.exitCode == 2),
           QStringLiteral("Could not inspect the recovery partition."));

    QTemporaryDir temporary(QStringLiteral("/run/cubelinux-recovery-status-XXXXXX"));
    ensure(temporary.isValid(), QStringLiteral("Could not create a temporary recovery check directory."));
    int matches = 0;
    for (const auto &candidate : lines(result.standardOutput)) {
        try {
            if (deviceInfo(candidate).disk != rootDevice.disk) {
                continue;
            }
            MountGuard mount(temporary.path());
            mount.mount(candidate, QStringLiteral("ro,nodev,nosuid,noexec"));
            const auto config = [&] {
                QFile file(temporary.path() + QStringLiteral("/active.cfg"));
                ensure(file.open(QIODevice::ReadOnly | QIODevice::Text),
                       QStringLiteral("recovery boot configuration is missing"));
                return QString::fromUtf8(file.readAll());
            }();

            static const QRegularExpression selector(QStringLiteral("^set recovery_slot=([AB])$"),
                                                      QRegularExpression::MultilineOption);
            auto iterator = selector.globalMatch(config);
            if (!iterator.hasNext()) {
                mount.unmount();
                continue;
            }
            const auto selected = iterator.next().captured(1);
            if (iterator.hasNext()) {
                mount.unmount();
                continue;
            }

            const auto recoveryId = blockId(candidate, QStringLiteral("PARTUUID"));
            if (lowercase(recoveryId) != lowercase(expectedRecoveryId) ||
                lowercase(blockId(candidate, QStringLiteral("UUID"))) != lowercase(expectedFsUuid) ||
                blockId(candidate, QStringLiteral("TYPE")) != QLatin1String("ext4")) {
                mount.unmount();
                continue;
            }

            const auto slot = temporary.path() + QStringLiteral("/slots/") + selected;
            const auto layout = verifyBundle(slot, checkContents);
            if (lowercase(layout.rootPartUuid) != lowercase(rootId) ||
                lowercase(layout.diskPtUuid) != lowercase(rootDiskId) ||
                lowercase(layout.efiPartUuid) != lowercase(efiId) ||
                lowercase(layout.recoveryPartUuid) != lowercase(recoveryId)) {
                mount.unmount();
                continue;
            }

            const auto runtimeSlot = activeRuntimeSlot(temporary.path());
            if (config == recoveryConfig(selected, recoveryId, runtimeSlot)) {
                ++matches;
            }
            mount.unmount();
        } catch (const std::exception &) {
            // A labelled partition may belong to another installation or contain
            // an incomplete slot. Continue checking other recovery candidates.
        }
    }
    return matches == 1;
}

BundleMetadata bootLayout(const QString &efiId, bool requireSecureBoot)
{
    const auto directory = kBootDirectory;
    const auto metadataPath = directory + QStringLiteral("/boot-layout");
    ensure(QFileInfo(metadataPath).isFile(),
           QStringLiteral("Recovery is not installed. Reinstall cubelinux to add factory recovery."));
    const auto fields = readFields(metadataPath);

    const QSet<QString> legacyFields = {
        QStringLiteral("recovery_partuuid"), QStringLiteral("recovery_fs_uuid"),
        QStringLiteral("efi_partuuid"), QStringLiteral("boot_sha256")};
    const QSet<QString> signedFields = {
        QStringLiteral("format"), QStringLiteral("recovery_partuuid"),
        QStringLiteral("recovery_fs_uuid"), QStringLiteral("efi_partuuid"),
        QStringLiteral("shim_sha256"), QStringLiteral("grub_sha256"),
        QStringLiteral("grub_cfg_sha256")};

    if (hasExactKeys(fields, legacyFields)) {
        ensure(!requireSecureBoot,
               QStringLiteral("Recovery needs an update before it can boot with Secure Boot enabled."));
        static const QRegularExpression digestPattern(QStringLiteral("^[0-9a-f]{64}$"));
        ensure(digestPattern.match(fields.value(QStringLiteral("boot_sha256"))).hasMatch(),
               QStringLiteral("The recovery boot metadata is invalid."));
        verifyFileDigest(directory + QStringLiteral("/recovery.efi"),
                         fields.value(QStringLiteral("boot_sha256")), QStringLiteral("recovery.efi"));
    } else if (hasExactKeys(fields, signedFields) && fields.value(QStringLiteral("format")) == QLatin1String("2")) {
        static const QRegularExpression digestPattern(QStringLiteral("^[0-9a-f]{64}$"));
        const auto fedoraDirectory = QStringLiteral("/boot/efi/EFI/fedora");
        for (const auto &entry : {
                 qMakePair(QStringLiteral("shimx64.efi"), QStringLiteral("shim_sha256")),
                 qMakePair(QStringLiteral("grubx64.efi"), QStringLiteral("grub_sha256")),
                 qMakePair(QStringLiteral("grub.cfg"), QStringLiteral("grub_cfg_sha256"))}) {
            const auto expected = fields.value(entry.second);
            ensure(digestPattern.match(expected).hasMatch(),
                   QStringLiteral("The recovery boot metadata is invalid."));
            const auto copied = directory + QLatin1Char('/') + entry.first;
            verifyFileDigest(copied, expected, entry.first);
            if (entry.first != QLatin1String("grub.cfg")) {
                const auto fedoraCopy = fedoraDirectory + QLatin1Char('/') + entry.first;
                QFile recoveryFile(copied);
                QFile fedoraFile(fedoraCopy);
                ensure(fedoraFile.open(QIODevice::ReadOnly) && recoveryFile.open(QIODevice::ReadOnly) &&
                           fedoraFile.readAll() == recoveryFile.readAll(),
                       QStringLiteral("The Fedora Secure Boot loader is stale or has changed."));
            }
        }
    } else {
        throw Failure(QStringLiteral("The recovery boot metadata is incomplete or unsupported."));
    }

    ensure(lowercase(fields.value(QStringLiteral("efi_partuuid"))) == lowercase(efiId),
           QStringLiteral("The recovery boot entry belongs to a different EFI partition."));
    ensure(isUuid(fields.value(QStringLiteral("recovery_partuuid"))) &&
               isUuid(fields.value(QStringLiteral("recovery_fs_uuid"))),
           QStringLiteral("The recovery boot metadata is invalid."));
    return {fields.value(QStringLiteral("recovery_partuuid")),
            fields.value(QStringLiteral("recovery_fs_uuid")), fields.value(QStringLiteral("efi_partuuid"))};
}

struct RecoveryEntry {
    QString id;
    QString efibootOutput;
};

RecoveryEntry recoveryEntry(bool checkContents)
{
    QFile secureBoot(kSecureBootVariable);
    ensure(secureBoot.open(QIODevice::ReadOnly), QStringLiteral("Could not determine the Secure Boot state."));
    const auto variable = secureBoot.readAll();
    ensure(variable.size() >= 5 && (variable[4] == 0 || variable[4] == 1),
           QStringLiteral("Could not determine the Secure Boot state."));
    const bool secureBootEnabled = variable[4] == 1;

    const auto efi = deviceSource(QStringLiteral("/boot/efi"));
    const auto efiId = blockId(efi, QStringLiteral("PARTUUID"));
    ensure(isUuid(efiId), QStringLiteral("Could not identify the EFI partition."));
    const auto metadata = bootLayout(efiId, secureBootEnabled);
    ensure(recoveryPartitionPresent(efiId, metadata.recoveryPartUuid,
                                    metadata.recoveryFsUuid, checkContents),
           QStringLiteral("The recovery partition is missing or does not match this installation."));

    const auto entries = run({QStringLiteral("/usr/sbin/efibootmgr"), QStringLiteral("-v")});
    static const QRegularExpression entryPattern(QStringLiteral("^Boot([0-9A-Fa-f]{4})\\*?\\s+cubelinux recovery\\s"));
    const auto signedLoader = QStringLiteral("file(\\efi\\cubelinux-recovery\\shimx64.efi)");
    const auto legacyLoader = QStringLiteral("file(\\efi\\cubelinux-recovery\\recovery.efi)");
    QStringList matches;
    for (const auto &line : lines(entries)) {
        const auto match = entryPattern.match(line);
        if (!match.hasMatch() || !line.toLower().contains(efiId.toLower())) {
            continue;
        }
        const auto normalized = line.toLower();
        if (secureBootEnabled && !normalized.contains(signedLoader)) {
            throw Failure(QStringLiteral("The recovery firmware entry does not use Fedora's Secure Boot loader."));
        }
        if (normalized.contains(signedLoader) || (!secureBootEnabled && normalized.contains(legacyLoader))) {
            matches.append(match.captured(1));
        }
    }
    ensure(matches.size() == 1, QStringLiteral("The recovery boot entry is missing or ambiguous."));
    return {matches.front(), entries};
}

void refreshRecoveryBootloader()
{
    const auto helper = QStringLiteral("/usr/lib/cubelinux-recovery/runtime/install-recovery-boot");
    ensure(QFileInfo(helper).isFile() && !isSymlink(helper),
           QStringLiteral("The signed recovery bootloader updater is missing."));
    run({helper, QStringLiteral("/")});
}

void writeStatus(const QString &contents)
{
    writeAtomically(QStringLiteral("/run/cubelinux-recovery-status"), contents.toUtf8(), 0644);
}

int statusCommand()
{
    try {
        recoveryEntry(false);
        writeStatus(QStringLiteral("available\n"));
    } catch (const std::exception &error) {
        writeStatus(QStringLiteral("unavailable\n") + QString::fromUtf8(error.what()) + QLatin1Char('\n'));
    }
    return 0;
}

int rebootCommand()
{
    refreshRecoveryBootloader();
    const auto entry = recoveryEntry(true);
    static const QRegularExpression previousPattern(QStringLiteral("^BootNext:\\s*([0-9A-Fa-f]{4})\\s*$"),
                                                     QRegularExpression::MultilineOption);
    const auto previousMatch = previousPattern.match(entry.efibootOutput);
    run({QStringLiteral("/usr/sbin/efibootmgr"), QStringLiteral("--bootnext"), entry.id});
    try {
        run({QStringLiteral("/usr/bin/systemctl"), QStringLiteral("reboot")});
    } catch (...) {
        if (previousMatch.hasMatch()) {
            run({QStringLiteral("/usr/sbin/efibootmgr"), QStringLiteral("--bootnext"), previousMatch.captured(1)});
        } else {
            run({QStringLiteral("/usr/sbin/efibootmgr"), QStringLiteral("--delete-bootnext")});
        }
        throw;
    }
    return 0;
}

} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    if (::geteuid() != 0) {
        qCritical("Recovery access requires administrator authorization.");
        return 1;
    }
    if (app.arguments().size() == 2 && app.arguments().at(1) == QLatin1String("--status")) {
        try {
            return statusCommand();
        } catch (const std::exception &error) {
            qCritical().noquote() << "Could not write recovery status:" << error.what();
            return 1;
        }
    }
    if (app.arguments().size() != 1) {
        qCritical("Usage: cubelinux-recovery-reboot [--status]");
        return 2;
    }
    try {
        return rebootCommand();
    } catch (const std::exception &error) {
        qCritical().noquote() << "Could not restart into recovery:" << error.what();
        return 1;
    }
}
