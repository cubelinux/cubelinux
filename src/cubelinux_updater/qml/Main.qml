import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("Updater")
    visible: false
    width: 760
    height: 560
    minimumWidth: 500
    minimumHeight: 460

    function statusHeading() {
        if (updateController.errorDetails.length > 0) {
            if (updateController.updateStaged) {
                return qsTr("Couldn't finish installing")
            }
            if (updateController.updateAvailable) {
                return qsTr("Download didn't finish")
            }
            return qsTr("Couldn't check for updates")
        }
        if (updateController.busy) {
            if (updateController.busyPhase === "download") {
                return qsTr("Downloading update")
            }
            if (updateController.busyPhase === "prepare") {
                return qsTr("Preparing update")
            }
            if (updateController.busyPhase === "check") {
                return qsTr("Checking for updates")
            }
            if (updateController.busyPhase === "apply") {
                return qsTr("Restarting to install")
            }
            return qsTr("Working on your update")
        }
        if (updateController.updateStaged) {
            return qsTr("Update downloaded")
        }
        if (updateController.updateAvailable) {
            return qsTr("An update is available")
        }
        return updateController.hasChecked
               ? qsTr("You're up to date")
               : qsTr("Ready to check for updates")
    }

    function primaryActionText() {
        if (updateController.busy) {
            return qsTr("Working…")
        }
        if (updateController.updateStaged) {
            return qsTr("Restart now")
        }
        if (updateController.updateAvailable) {
            return updateController.errorDetails.length > 0
                   ? qsTr("Try again") : qsTr("Download update")
        }
        if (updateController.hasChecked) {
            return updateController.errorDetails.length > 0
                   ? qsTr("Try again") : qsTr("Check again")
        }
        return qsTr("Check for updates")
    }

    pageStack.initialPage: Kirigami.ScrollablePage {
        title: qsTr("System updates")
        padding: Kirigami.Units.largeSpacing

        ColumnLayout {
            width: parent.width
            spacing: Kirigami.Units.largeSpacing

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Heading {
                    Layout.fillWidth: true
                    text: qsTr("System updates")
                    level: 1
                }

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("Keep cubelinux up to date.")
                    opacity: 0.75
                    wrapMode: Text.Wrap
                }
            }

            Kirigami.Card {
                Layout.fillWidth: true

                contentItem: ColumnLayout {
                    spacing: Kirigami.Units.mediumSpacing

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.mediumSpacing

                        Kirigami.Icon {
                            Layout.preferredWidth: Kirigami.Units.iconSizes.large
                            Layout.preferredHeight: Kirigami.Units.iconSizes.large
                            source: updateController.errorDetails.length > 0
                                    ? "dialog-error"
                                    : updateController.updateStaged
                                      ? "system-reboot"
                                      : updateController.updateAvailable
                                        ? "software-update-available"
                                        : updateController.hasChecked
                                          ? "emblem-success"
                                          : "system-software-update"
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Kirigami.Heading {
                                Layout.fillWidth: true
                                text: root.statusHeading()
                                level: 2
                                wrapMode: Text.Wrap
                            }

                            Controls.Label {
                                Layout.fillWidth: true
                                visible: !updateController.busy
                                         && updateController.errorDetails.length === 0
                                text: updateController.statusText
                                opacity: 0.78
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        visible: updateController.latestVersion.length > 0
                                 || updateController.latestUpdated.length > 0

                        Kirigami.Separator {
                            Layout.fillWidth: true
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            visible: updateController.latestVersion.length > 0
                            text: (updateController.updateAvailable || updateController.updateStaged)
                                  ? qsTr("New system version: %1").arg(updateController.latestVersion)
                                  : qsTr("Installed system version: %1").arg(updateController.latestVersion)
                            font.bold: true
                            wrapMode: Text.Wrap
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            visible: updateController.latestUpdated.length > 0
                            text: (updateController.updateAvailable || updateController.updateStaged)
                                  ? qsTr("Build date: %1").arg(updateController.latestUpdated)
                                  : qsTr("Installed image date: %1").arg(updateController.latestUpdated)
                            opacity: 0.75
                            wrapMode: Text.Wrap
                        }
                    }

                    Kirigami.InlineMessage {
                        Layout.fillWidth: true
                        visible: updateController.errorDetails.length > 0
                        type: Kirigami.MessageType.Error
                        text: updateController.statusText
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        visible: updateController.errorDetails.length > 0
                        text: updateController.errorDetails
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                        opacity: 0.8
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        visible: updateController.busy

                        RowLayout {
                            Layout.fillWidth: true
                            visible: updateController.busyPhase === "download"
                                     && updateController.progressPercent >= 0

                            Controls.Label {
                                Layout.fillWidth: true
                                text: qsTr("Downloading system image")
                                font.bold: true
                            }

                            Controls.Label {
                                text: qsTr("%1%").arg(updateController.progressPercent)
                                font.bold: true
                            }
                        }

                        Controls.ProgressBar {
                            Layout.fillWidth: true
                            from: 0
                            to: 100
                            value: Math.max(0, updateController.progressPercent)
                            indeterminate: updateController.progressPercent < 0
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            visible: updateController.busyPhase === "download"
                            text: qsTr("You can keep using your PC while the update downloads.")
                            opacity: 0.72
                            wrapMode: Text.Wrap
                        }
                    }

                    Controls.Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 46
                        text: root.primaryActionText()
                        icon.name: updateController.updateStaged
                                   ? "system-reboot"
                                   : updateController.updateAvailable
                                     ? "download"
                                     : "view-refresh"
                        enabled: !updateController.busy
                        highlighted: true
                        onClicked: {
                            if (updateController.updateStaged) {
                                rebootConfirmation.open()
                            } else if (updateController.updateAvailable) {
                                updateController.stageUpdate()
                            } else {
                                updateController.checkForUpdates()
                            }
                        }
                    }
                }
            }

            Controls.Label {
                Layout.alignment: Qt.AlignRight
                text: qsTr("cubelinux / Updater %1").arg(softwareVersion)
                opacity: 0.55
                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
            }
        }
    }

    Controls.Dialog {
        id: rebootConfirmation
        title: qsTr("Restart to finish updating?")
        modal: true
        width: Math.min(root.width - Kirigami.Units.largeSpacing * 2, 460)

        ColumnLayout {
            width: parent.width
            spacing: Kirigami.Units.mediumSpacing

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("Your PC will restart to finish installing the update. Save your work before continuing.")
                wrapMode: Text.Wrap
            }

            RowLayout {
                Layout.fillWidth: true

                Item { Layout.fillWidth: true }

                Controls.Button {
                    text: qsTr("Later")
                    onClicked: rebootConfirmation.reject()
                }

                Controls.Button {
                    text: qsTr("Restart now")
                    icon.name: "system-reboot"
                    highlighted: true
                    onClicked: {
                        rebootConfirmation.accept()
                        updateController.applyAndReboot()
                    }
                }
            }
        }
    }
}
