import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts

Controls.ApplicationWindow {
    id: root

    title: qsTr("Updater")
    visible: false
    width: 640
    height: 648
    minimumWidth: 540
    minimumHeight: 520

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
        if (updateController.hasChecked && updateController.errorDetails.length > 0) {
            return qsTr("Try again")
        }
        return qsTr("Check for updates")
    }

    footer: Controls.ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 32
            anchors.rightMargin: 32
            spacing: 8

            Controls.Label {
                text: qsTr("cubelinux · Updater %1").arg(softwareVersion)
                opacity: 0.7
            }

            Item {
                Layout.fillWidth: true
            }

            Controls.Button {
                visible: updateController.updateAvailable || updateController.updateStaged
                text: qsTr("Later")
                onClicked: {
                    if (!previewMode) {
                        root.hide()
                    }
                }
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
        anchors.fill: parent
        anchors.leftMargin: 32
        anchors.rightMargin: 32
        anchors.topMargin: 40
        anchors.bottomMargin: 24
        spacing: 20

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("System updates")
                font.pixelSize: 24
                font.weight: Font.DemiBold
            }

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("Keep cubelinux up to date.")
                opacity: 0.75
                wrapMode: Text.Wrap
            }
        }

        Controls.Frame {
            Layout.fillWidth: true
            Layout.minimumHeight: 96

            RowLayout {
                spacing: 16

                Controls.Label {
                    Layout.preferredWidth: 36
                    text: updateController.errorDetails.length > 0
                          ? "!" : updateController.updateStaged ? "↻"
                          : updateController.updateAvailable ? "↓"
                          : updateController.hasChecked ? "✓" : "↻"
                    font.pixelSize: 30
                    horizontalAlignment: Text.AlignHCenter
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Controls.Label {
                        Layout.fillWidth: true
                        text: root.statusHeading()
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
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
            Layout.topMargin: 32
            columns: 2
            columnSpacing: 20
            rowSpacing: 16
            visible: updateController.latestVersion.length > 0
                     || updateController.latestUpdated.length > 0

            Controls.Label {
                Layout.columnSpan: 2
                Layout.fillWidth: true
                text: (updateController.updateAvailable || updateController.updateStaged)
                      ? qsTr("UPDATE DETAILS") : qsTr("INSTALLED SYSTEM")
                opacity: 0.7
                font.bold: true
                font.pixelSize: 13
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

            Controls.Control {
                Layout.columnSpan: 2
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                padding: 0
                background: Rectangle {
                    implicitHeight: 1
                    color: parent.palette.mid
                }
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

        Controls.Label {
            Layout.fillWidth: true
            visible: updateController.errorDetails.length > 0
            text: updateController.statusText + "\n" + updateController.errorDetails
            wrapMode: Text.Wrap
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
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

        Item {
            Layout.fillHeight: true
        }
    }

    Controls.Dialog {
        id: rebootConfirmation
        title: qsTr("Restart to finish updating?")
        modal: true
        width: Math.min(root.width - 48, 460)

        ColumnLayout {
            width: parent.width
            spacing: 16

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
