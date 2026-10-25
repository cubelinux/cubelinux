import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("bootc Updater")
    width: 760
    height: 680
    minimumWidth: 500
    minimumHeight: 560

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
                        text: qsTr("Manage your system image and staged updates.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }
                }

                Rectangle {
                    Layout.alignment: Qt.AlignTop
                    radius: height / 2
                    color: Qt.rgba(Kirigami.Theme.disabledTextColor.r,
                                   Kirigami.Theme.disabledTextColor.g,
                                   Kirigami.Theme.disabledTextColor.b, 0.12)
                    width: previewLabel.implicitWidth + Kirigami.Units.largeSpacing
                    height: previewLabel.implicitHeight + Kirigami.Units.smallSpacing

                    Controls.Label {
                        id: previewLabel
                        anchors.centerIn: parent
                        text: qsTr("PREVIEW")
                        font.bold: true
                        font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: deploymentLayout.implicitHeight + Kirigami.Units.largeSpacing * 2
                radius: Kirigami.Units.mediumSpacing
                color: Kirigami.Theme.backgroundColor
                border.color: Kirigami.Theme.separatorColor

                RowLayout {
                    id: deploymentLayout
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.largeSpacing
                    spacing: Kirigami.Units.mediumSpacing

                    Rectangle {
                        Layout.preferredWidth: Kirigami.Units.iconSizes.large + Kirigami.Units.mediumSpacing
                        Layout.preferredHeight: Kirigami.Units.iconSizes.large + Kirigami.Units.mediumSpacing
                        radius: Kirigami.Units.mediumSpacing
                        color: Kirigami.Theme.alternateBackgroundColor

                        Kirigami.Icon {
                            anchors.centerIn: parent
                            width: Kirigami.Units.iconSizes.large
                            height: width
                            source: "computer"
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        Controls.Label {
                            text: qsTr("CURRENT DEPLOYMENT")
                            font.bold: true
                            font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                            opacity: 0.7
                        }

                        Kirigami.Heading {
                            Layout.fillWidth: true
                            text: qsTr("Fedora bootc image")
                            level: 3
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            text: qsTr("Updates are installed as a new image deployment.")
                            opacity: 0.75
                            wrapMode: Text.Wrap
                        }
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

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        visible: updateController.busy

                        Controls.Label {
                            Layout.fillWidth: true
                            text: updateController.statusText
                            wrapMode: Text.Wrap
                        }

                        Controls.ProgressBar {
                            Layout.fillWidth: true
                            indeterminate: true
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.mediumSpacing

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Controls.Label {
                                text: qsTr("CHECK FOR UPDATES")
                                font.bold: true
                                font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                                opacity: 0.7
                            }

                            Controls.Label {
                                Layout.fillWidth: true
                                text: qsTr("Checks the configured image registry without downloading or staging an update.")
                                wrapMode: Text.Wrap
                            }
                        }

                        Controls.Button {
                            text: updateController.busy ? qsTr("Working...") : qsTr("Check for updates")
                            icon.name: "view-refresh"
                            enabled: !updateController.busy
                            onClicked: updateController.checkForUpdates()
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.mediumSpacing

                        Controls.Button {
                            text: qsTr("Stage update")
                            icon.name: "download"
                            enabled: updateController.updateAvailable && !updateController.busy
                            onClicked: updateController.stageUpdate()
                        }

                        Controls.Button {
                            text: qsTr("Apply & reboot")
                            icon.name: "system-reboot"
                            visible: updateController.updateStaged
                            enabled: updateController.updateStaged && !updateController.busy
                            onClicked: rebootConfirmation.open()
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: historyLayout.implicitHeight + Kirigami.Units.largeSpacing * 2
                radius: Kirigami.Units.mediumSpacing
                color: Kirigami.Theme.backgroundColor
                border.color: Kirigami.Theme.separatorColor

                ColumnLayout {
                    id: historyLayout
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.largeSpacing
                    spacing: Kirigami.Units.mediumSpacing

                    RowLayout {
                        Layout.fillWidth: true

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Kirigami.Heading {
                                text: qsTr("Image history on this device")
                                level: 2
                            }

                            Controls.Label {
                                Layout.fillWidth: true
                                text: qsTr("Shows images bootc still tracks locally. It does not list every tag published in GitHub Container Registry.")
                                opacity: 0.75
                                wrapMode: Text.Wrap
                            }
                        }

                        Controls.Button {
                            text: qsTr("Refresh")
                            icon.name: "view-refresh"
                            enabled: !updateController.busy
                            onClicked: updateController.refreshImageHistory()
                        }
                    }

                    Kirigami.Separator {
                        Layout.fillWidth: true
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        visible: updateController.imageHistory.length === 0
                        text: qsTr("Select Refresh to load the current, staged, and rollback deployments.")
                        wrapMode: Text.Wrap
                    }

                    Repeater {
                        model: updateController.imageHistory

                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            RowLayout {
                                Layout.fillWidth: true

                                Controls.Label {
                                    text: modelData.role
                                    font.bold: true
                                }

                                Controls.Label {
                                    Layout.fillWidth: true
                                    text: modelData.version
                                    horizontalAlignment: Text.AlignRight
                                    opacity: 0.75
                                }
                            }

                            Controls.Label {
                                Layout.fillWidth: true
                                text: modelData.image
                                wrapMode: Text.WrapAnywhere
                            }

                            Controls.Label {
                                Layout.fillWidth: true
                                text: modelData.digest
                                font.family: "monospace"
                                font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                                opacity: 0.65
                                wrapMode: Text.WrapAnywhere
                            }

                            Kirigami.Separator {
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.mediumSpacing

                Kirigami.Heading {
                    Layout.fillWidth: true
                    text: qsTr("How updates work")
                    level: 3
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width < 620 ? 1 : 3
                    columnSpacing: Kirigami.Units.mediumSpacing
                    rowSpacing: Kirigami.Units.mediumSpacing

                    Repeater {
                        model: [
                            { number: "1", title: qsTr("Check"), description: qsTr("Look for a newer system image.") },
                            { number: "2", title: qsTr("Stage"), description: qsTr("Download it as the next deployment.") },
                            { number: "3", title: qsTr("Restart"), description: qsTr("Boot into the updated system.") }
                        ]

                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            implicitHeight: stepLayout.implicitHeight + Kirigami.Units.mediumSpacing * 2
                            radius: Kirigami.Units.mediumSpacing
                            color: Kirigami.Theme.alternateBackgroundColor

                            RowLayout {
                                id: stepLayout
                                anchors.fill: parent
                                anchors.margins: Kirigami.Units.mediumSpacing
                                spacing: Kirigami.Units.mediumSpacing

                                Rectangle {
                                    Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                                    Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                                    radius: width / 2
                                    color: Kirigami.Theme.backgroundColor

                                    Controls.Label {
                                        anchors.centerIn: parent
                                        text: modelData.number
                                        font.bold: true
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.smallSpacing

                                    Controls.Label {
                                        text: modelData.title
                                        font.bold: true
                                    }

                                    Controls.Label {
                                        Layout.fillWidth: true
                                        text: modelData.description
                                        opacity: 0.75
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("A staged update becomes active after reboot.")
                horizontalAlignment: Text.AlignHCenter
                opacity: 0.65
                wrapMode: Text.Wrap
            }
        }
    }

    Controls.Dialog {
        id: rebootConfirmation
        title: qsTr("Apply staged update?")
        modal: true
        standardButtons: Controls.Dialog.Cancel | Controls.Dialog.Ok

        Controls.Label {
            text: qsTr("The system will reboot to apply the staged image. Save your work before continuing.")
            wrapMode: Text.Wrap
        }

        onAccepted: updateController.applyAndReboot()
    }
}
