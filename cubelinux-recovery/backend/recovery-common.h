#pragma once

#include <QByteArray>
#include <QMap>
#include <QString>
#include <QStringList>

#include <stdexcept>

namespace Recovery {

class Failure : public std::runtime_error {
public:
    explicit Failure(const QString &message);
};

void ensure(bool condition, const QString &message);

struct ProcessResult {
    int exitCode = -1;
    bool normalExit = false;
    QString standardOutput;
    QString standardError;
};

struct DeviceInfo {
    QString partition;
    QString disk;
};

struct Layout {
    QString diskPtUuid;
    QString rootPartUuid;
    QString recoveryPartUuid;
    QString efiPartUuid;
};

struct BundleMetadata {
    QString recoveryPartUuid;
    QString recoveryFsUuid;
    QString efiPartUuid;
};

ProcessResult runResult(const QStringList &arguments, int timeoutMs = -1,
                        const QMap<QString, QString> &environment = {});
QString run(const QStringList &arguments, int timeoutMs = -1,
            const QMap<QString, QString> &environment = {});
QStringList lines(const QString &text);
QString deviceSource(const QString &mountPoint);
QString systemRootSource();
DeviceInfo deviceInfo(const QString &device);
QString blockId(const QString &device, const QString &tag);
QString sha256File(const QString &path);
QMap<QString, QString> readFields(const QString &path);
Layout parseLayout(const QString &path);
Layout verifyBundle(const QString &slot, bool checkContents = true);
QString activeSlot(const QString &mount);
QString activeRuntimeSlot(const QString &mount);
QString recoveryConfig(const QString &slot, const QString &recoveryId,
                       const QString &runtimeSlot = {});
void writeAtomically(const QString &path, const QByteArray &contents, unsigned int mode = 0644);
void syncDirectory(const QString &path);
void copyFilePreservingDestination(const QString &source, const QString &destination);
void copyTreeOverlay(const QString &source, const QString &destination);
void removeTree(const QString &path);
bool isUuid(const QString &value);
bool isSymlink(const QString &path);

class MountGuard {
public:
    explicit MountGuard(QString target);
    MountGuard(const MountGuard &) = delete;
    MountGuard &operator=(const MountGuard &) = delete;
    ~MountGuard();

    void mount(const QString &device, const QString &options);
    void unmount();
    bool mounted() const;

private:
    QString m_target;
    bool m_mounted = false;
};

} // namespace Recovery
