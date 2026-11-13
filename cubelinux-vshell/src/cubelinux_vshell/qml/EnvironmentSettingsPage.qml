import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    property var controller
    property string environmentId: "vshell"
    property string environmentName: qsTr("cubelinux Runtime")
    signal returnToWorkspaceRequested()
    signal aboutRequested()

    title: qsTr("Environment settings")
    actions: [
        Kirigami.Action {
            text: qsTr("Menu")
            icon.name: "application-menu"
            children: [
                Kirigami.Action {
                    text: qsTr("About Linux Subsystem")
                    icon.name: "help-about"
                    onTriggered: page.aboutRequested()
                }
            ]
        }
    ]

    ColumnLayout {
        id: content

        width: page.availableWidth
        height: Math.max(page.availableHeight, content.implicitHeight)
        spacing: 0

        Item {
            Layout.fillHeight: true
            Layout.minimumHeight: Kirigami.Units.largeSpacing
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 48
            Layout.alignment: Qt.AlignHCenter
            spacing: Kirigami.Units.largeSpacing * 1.5

            Controls.Button {
                Layout.alignment: Qt.AlignLeft
                text: qsTr("Back to environments")
                icon.name: "go-previous"
                onClicked: page.returnToWorkspaceRequested()
            }

            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: controller.folderSharingMessage.length > 0
                text: controller.folderSharingMessage
                type: controller.folderSharingError
                      ? Kirigami.MessageType.Error : Kirigami.MessageType.Information
            }

            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: controller.portForwardingMessage.length > 0
                text: controller.portForwardingMessage
                type: Kirigami.MessageType.Error
            }

            Controls.ProgressBar {
                Layout.fillWidth: true
                visible: controller.folderSharingBusy
                indeterminate: true
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.mediumSpacing

                Kirigami.Heading {
                    Layout.fillWidth: true
                    text: qsTr("Shared folders")
                    level: 2
                }

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("Choose which cubelinux folders are available to %1.").arg(page.environmentName)
                    opacity: 0.75
                    wrapMode: Text.Wrap
                }

                Kirigami.Card {
                    Layout.fillWidth: true

                    contentItem: ColumnLayout {
                        spacing: Kirigami.Units.mediumSpacing

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.mediumSpacing

                            Kirigami.Icon {
                                source: "folder-home"
                                implicitWidth: Kirigami.Units.iconSizes.medium
                                implicitHeight: Kirigami.Units.iconSizes.medium
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.smallSpacing

                                Controls.Label {
                                    text: qsTr("Home folder")
                                    font.bold: true
                                }

                                Controls.Label {
                                    Layout.fillWidth: true
                                    text: qsTr("Shared with %1 at %2.").arg(page.environmentName).arg(controller.sharedHomePath)
                                    opacity: 0.75
                                    wrapMode: Text.Wrap
                                }
                            }

                            Controls.Label {
                                text: qsTr("Shared")
                                opacity: 0.75
                            }
                        }

                        Kirigami.Separator {
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.smallSpacing

                                Kirigami.Heading {
                                    text: qsTr("Additional folders")
                                    level: 3
                                }

                                Controls.Label {
                                    Layout.fillWidth: true
                                    visible: controller.sharedFolders.length === 0
                                    text: qsTr("No additional folders are shared.")
                                    opacity: 0.75
                                    wrapMode: Text.Wrap
                                }
                            }

                            Controls.Button {
                                text: qsTr("Add folder…")
                                icon.name: "folder-open"
                                enabled: !controller.busy && !controller.folderSharingBusy
                                         && !controller.destroying
                                onClicked: controller.chooseSharedFolder()
                            }
                        }

                        Repeater {
                            model: controller.sharedFolders

                            delegate: RowLayout {
                                required property var modelData

                                Layout.fillWidth: true
                                spacing: Kirigami.Units.mediumSpacing

                                Kirigami.Icon {
                                    source: "folder"
                                    implicitWidth: Kirigami.Units.iconSizes.small
                                    implicitHeight: Kirigami.Units.iconSizes.small
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.smallSpacing

                                    Controls.Label {
                                        Layout.fillWidth: true
                                        text: modelData.name
                                        font.bold: true
                                        elide: Text.ElideMiddle
                                    }

                                    Controls.Label {
                                        Layout.fillWidth: true
                                        text: modelData.available === "true"
                                              ? qsTr("%1 → %2").arg(modelData.path).arg(modelData.mountPath)
                                              : qsTr("Folder not found: %1").arg(modelData.path)
                                        opacity: modelData.available === "true" ? 0.75 : 1.0
                                        color: modelData.available === "true" ? Kirigami.Theme.textColor
                                                                               : Kirigami.Theme.negativeTextColor
                                        elide: Text.ElideMiddle
                                    }
                                }

                                Controls.ToolButton {
                                    icon.name: "edit-delete"
                                    Accessible.name: qsTr("Remove shared folder")
                                    Controls.ToolTip.text: qsTr("Remove shared folder")
                                    enabled: !controller.busy && !controller.folderSharingBusy
                                             && !controller.destroying
                                    onClicked: controller.removeSharedFolder(modelData.id)
                                }
                            }
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            text: qsTr("%1 can read and modify shared folders. Changing folder access restarts it if it is running.").arg(page.environmentName)
                            opacity: 0.75
                            wrapMode: Text.Wrap
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.mediumSpacing

                Kirigami.Heading {
                    Layout.fillWidth: true
                    text: qsTr("Port forwarding")
                    level: 2
                }

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("%1 TCP services on ports 1024 and above are forwarded to this host automatically.").arg(page.environmentName)
                    opacity: 0.75
                    wrapMode: Text.Wrap
                }

                Kirigami.Card {
                    Layout.fillWidth: true

                    contentItem: ColumnLayout {
                        spacing: Kirigami.Units.mediumSpacing

                        Controls.Label {
                            Layout.fillWidth: true
                            visible: controller.forwardedPorts.length === 0
                            text: qsTr("No forwarded ports detected. Start a network service in %1 to see it here.").arg(page.environmentName)
                            opacity: 0.75
                            wrapMode: Text.Wrap
                        }

                        Repeater {
                            model: controller.forwardedPorts

                            delegate: ColumnLayout {
                                required property var modelData
                                required property int index

                                Layout.fillWidth: true
                                spacing: Kirigami.Units.mediumSpacing

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.mediumSpacing

                                    Kirigami.Icon {
                                        source: "network-server"
                                        implicitWidth: Kirigami.Units.iconSizes.medium
                                        implicitHeight: Kirigami.Units.iconSizes.medium
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: Kirigami.Units.smallSpacing

                                        Controls.Label {
                                            text: qsTr("TCP port %1 in %2").arg(modelData.port).arg(page.environmentName)
                                            font.bold: true
                                        }

                                        Controls.Label {
                                            Layout.fillWidth: true
                                            text: modelData.status === "Forwarding"
                                                  ? qsTr("Available on this host at %1").arg(modelData.hostAddress)
                                                  : qsTr("Could not forward this port: %1").arg(modelData.error)
                                            opacity: modelData.status === "Forwarding" ? 0.75 : 1.0
                                            color: modelData.status === "Forwarding"
                                                   ? Kirigami.Theme.textColor : Kirigami.Theme.negativeTextColor
                                            wrapMode: Text.Wrap
                                        }
                                    }

                                    ColumnLayout {
                                        spacing: Kirigami.Units.smallSpacing

                                        Controls.Label {
                                            text: qsTr("Expose to public")
                                            font.bold: true
                                        }

                                        Controls.Switch {
                                            checked: modelData.publicAccess
                                            Accessible.name: qsTr("Expose port %1 to public networks").arg(modelData.port)
                                            onToggled: controller.setPortPublicAccess(modelData.port, checked)
                                        }
                                    }
                                }

                                Kirigami.Separator {
                                    Layout.fillWidth: true
                                    visible: index < controller.forwardedPorts.length - 1
                                }
                            }
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            visible: controller.forwardedPorts.length > 0
                            text: qsTr("Public exposure listens on all host IPv4 interfaces. Your host firewall still controls incoming connections.")
                            opacity: 0.75
                            wrapMode: Text.Wrap
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
            Layout.minimumHeight: Kirigami.Units.largeSpacing
        }
    }
}
