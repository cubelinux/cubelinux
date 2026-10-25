import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("bootc Updater")
    visible: false
    width: 760
    height: 560
    minimumWidth: 500
    minimumHeight: 460

    pageStack.initialPage: Kirigami.ScrollablePage {
        title: qsTr("System updates")
        padding: Kirigami.Units.largeSpacing

        ColumnLayout {
            width: parent.width
            spacing: Kirigami.Units.largeSpacing

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.mediumSpacing

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
                        text: qsTr("Check for updates and install them when you're ready.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: updateLayout.implicitHeight + Kirigami.Units.largeSpacing * 2
                radius: Kirigami.Units.mediumSpacing
                color: Kirigami.Theme.backgroundColor
                border.color: Kirigami.Theme.separatorColor

                ColumnLayout {
                    id: updateLayout
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.largeSpacing
                    spacing: Kirigami.Units.mediumSpacing

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.mediumSpacing

                        Kirigami.Icon {
                            Layout.preferredWidth: Kirigami.Units.iconSizes.large
                            Layout.preferredHeight: Kirigami.Units.iconSizes.large
                            source: "system-software-update"
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Kirigami.Heading {
                                Layout.fillWidth: true
                                text: qsTr("Update status")
                                level: 2
                            }

                            Controls.Label {
                                Layout.fillWidth: true
                                text: updateController.statusText
                                opacity: 0.75
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                    Kirigami.Separator {
                        Layout.fillWidth: true
                    }

                    Controls.ProgressBar {
                        Layout.fillWidth: true
                        visible: updateController.busy
                        from: 0
                        to: 100
                        value: Math.max(0, updateController.progressPercent)
                        indeterminate: updateController.progressPercent < 0
                    }

                    Controls.Button {
                        Layout.fillWidth: true
                        text: updateController.busy ? updateController.busyText
                              : updateController.updateStaged ? qsTr("Restart now")
                              : updateController.updateAvailable ? qsTr("Update now")
                              : updateController.hasChecked ? qsTr("Check again")
                              : qsTr("Check for updates")
                        icon.name: updateController.updateStaged ? "system-reboot"
                                   : updateController.updateAvailable ? "download"
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

        }
    }

    Controls.Dialog {
        id: rebootConfirmation
        title: qsTr("Restart to finish updating?")
        modal: true

        Controls.Label {
            text: qsTr("Your PC will restart to finish installing the update. Save your work before continuing.")
            wrapMode: Text.Wrap
        }

        footer: RowLayout {
            spacing: Kirigami.Units.smallSpacing

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
