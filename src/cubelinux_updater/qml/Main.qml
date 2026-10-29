import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("Updater")
    visible: false
    width: 680
    height: 500
    minimumWidth: 520
    minimumHeight: 420

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
                   ? qsTr("Try again") : qsTr("Check for updates")
        }
        return qsTr("Check for updates")
    }

    function statusDescription() {
        if (updateController.updateStaged) {
            return qsTr("Restart your PC to finish applying the update.")
        }
        if (updateController.updateAvailable) {
            return qsTr("Download it now. You can keep using your PC while it downloads.")
        }
        if (updateController.hasChecked) {
            return qsTr("No updates are available right now.")
        }
        return updateController.statusText
    }

    pageStack.initialPage: Kirigami.ScrollablePage {
        title: qsTr("System updates")
        padding: Kirigami.Units.largeSpacing
        footer: Controls.ToolBar {
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Kirigami.Units.largeSpacing
                anchors.rightMargin: Kirigami.Units.largeSpacing
                spacing: Kirigami.Units.smallSpacing

                Controls.Label {
                    text: qsTr("cubelinux · Updater %1").arg(softwareVersion)
                    opacity: 0.65
                    font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                }

                Item {
                    Layout.fillWidth: true
                }

                Controls.Button {
                    visible: updateController.updateAvailable || updateController.updateStaged
                    text: qsTr("Later")
                    onClicked: root.hide()
                }

                Controls.Button {
                    text: root.primaryActionText()
                    enabled: !updateController.busy
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

        ColumnLayout {
            width: parent.width
            spacing: Kirigami.Units.largeSpacing

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("Keep cubelinux up to date.")
                opacity: 0.75
                wrapMode: Text.Wrap
            }

            Kirigami.Card {
                Layout.fillWidth: true

                contentItem: RowLayout {
                    spacing: Kirigami.Units.mediumSpacing

                    Kirigami.Icon {
                        Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                        Layout.preferredHeight: Kirigami.Units.iconSizes.medium
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
                            text: root.statusDescription()
                            opacity: 0.78
                            wrapMode: Text.Wrap
                        }
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: Kirigami.Units.largeSpacing
                rowSpacing: Kirigami.Units.smallSpacing
                visible: updateController.latestVersion.length > 0
                         || updateController.latestUpdated.length > 0

                Controls.Label {
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    text: (updateController.updateAvailable || updateController.updateStaged)
                          ? qsTr("UPDATE DETAILS") : qsTr("INSTALLED SYSTEM")
                    opacity: 0.7
                    font.bold: true
                    font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                }

                Controls.Label {
                    visible: updateController.latestVersion.length > 0
                    text: (updateController.updateAvailable || updateController.updateStaged)
                          ? qsTr("Available version") : qsTr("Version")
                    opacity: 0.75
                }

                Controls.Label {
                    Layout.fillWidth: true
                    visible: updateController.latestVersion.length > 0
                    text: updateController.latestVersion
                    horizontalAlignment: Text.AlignRight
                    wrapMode: Text.Wrap
                }

                Kirigami.Separator {
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    visible: updateController.latestVersion.length > 0
                             && updateController.latestUpdated.length > 0
                }

                Controls.Label {
                    visible: updateController.latestUpdated.length > 0
                    text: (updateController.updateAvailable || updateController.updateStaged)
                          ? qsTr("Build date") : qsTr("Image date")
                    opacity: 0.75
                }

                Controls.Label {
                    Layout.fillWidth: true
                    visible: updateController.latestUpdated.length > 0
                    text: updateController.latestUpdated
                    horizontalAlignment: Text.AlignRight
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
                    }

                    Controls.Label {
                        text: qsTr("%1% download").arg(updateController.progressPercent)
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
                    onClicked: {
                        rebootConfirmation.accept()
                        updateController.applyAndReboot()
                    }
                }
            }
        }
    }
}
