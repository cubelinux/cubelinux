import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: page

    property var controller
    property bool darkTheme: false
    signal destroyRequested()

    readonly property string containerStatusLabel: controller.destroying
        ? qsTr("Destroying Fedora")
        : controller.folderSharingBusy
          ? qsTr("Updating folder access")
          : controller.containerStatus === "running" ? qsTr("Running") : qsTr("Stopped")
    readonly property string containerStatusIcon: controller.destroying || controller.folderSharingBusy
        ? "view-refresh"
        : controller.containerStatus === "running" ? "media-playback-start" : "media-playback-stop"
    readonly property color containerStatusColor: controller.destroying || controller.folderSharingBusy
        ? Kirigami.Theme.neutralTextColor
        : controller.containerStatus === "running"
          ? Kirigami.Theme.positiveTextColor : Kirigami.Theme.negativeTextColor

    spacing: Kirigami.Units.largeSpacing

    ColumnLayout {
        Layout.fillWidth: true
        spacing: Kirigami.Units.smallSpacing

        Kirigami.Heading {
            text: qsTr("Linux environments")
            level: 1
        }

        Controls.Label {
            text: qsTr("Your container environments, ready to open.")
            opacity: 0.7
        }
    }

    Kirigami.InlineMessage {
        Layout.fillWidth: true
        visible: controller.busy
                 || controller.progressTitle === qsTr("Setup failed")
                 || controller.progressTitle === qsTr("Destroy failed")
        text: controller.progress
        type: controller.progressTitle === qsTr("Setup failed")
              || controller.progressTitle === qsTr("Destroy failed")
              ? Kirigami.MessageType.Error : Kirigami.MessageType.Information
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

    Controls.Label {
        Layout.leftMargin: Kirigami.Units.smallSpacing
        text: qsTr("Installed environments")
        font.bold: true
        opacity: 0.75
    }

    Controls.ProgressBar {
        Layout.fillWidth: true
        visible: controller.busy || controller.folderSharingBusy
        indeterminate: true
    }

    Kirigami.Card {
        Layout.fillWidth: true
        Layout.preferredHeight: 96
        Layout.minimumHeight: 96

        contentItem: RowLayout {
            spacing: Kirigami.Units.largeSpacing

            Image {
                source: page.darkTheme
                        ? "file:///usr/share/fedora-logos/fedora_logo_darkbackground.svg"
                        : "file:///usr/share/fedora-logos/fedora_logo.svg"
                sourceSize.width: 144
                sourceSize.height: 72
                fillMode: Image.PreserveAspectFit
                smooth: true
                Layout.preferredWidth: 64
                Layout.preferredHeight: Kirigami.Units.iconSizes.large
                Layout.alignment: Qt.AlignVCenter
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                Layout.alignment: Qt.AlignVCenter

                RowLayout {
                    spacing: Kirigami.Units.mediumSpacing

                    Kirigami.Heading {
                        text: qsTr("Fedora 44")
                        level: 2
                    }

                    Controls.Label {
                        text: qsTr("DEFAULT")
                        font.bold: true
                        font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                        opacity: 0.7
                    }
                }

                Controls.Label {
                    text: qsTr("Fedora Linux · x86_64")
                    opacity: 0.7
                }
            }

            Item {
                Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                Layout.alignment: Qt.AlignVCenter

                Kirigami.Icon {
                    id: statusIcon
                    anchors.centerIn: parent
                    source: page.containerStatusIcon
                    color: page.containerStatusColor
                    implicitWidth: Kirigami.Units.iconSizes.medium
                    implicitHeight: Kirigami.Units.iconSizes.medium
                    Accessible.name: page.containerStatusLabel

                    RotationAnimation on rotation {
                        from: 0
                        to: 360
                        duration: 1000
                        loops: Animation.Infinite
                        running: controller.destroying || controller.folderSharingBusy
                        onRunningChanged: if (!running) statusIcon.rotation = 0
                    }
                }
            }

            Controls.Button {
                Layout.alignment: Qt.AlignVCenter
                text: qsTr("Open terminal")
                icon.name: "utilities-terminal"
                highlighted: true
                enabled: !controller.busy
                         && !controller.destroying
                         && !controller.folderSharingBusy
                         && controller.progressTitle !== qsTr("Setup failed")
                onClicked: controller.openShell()
            }

            Controls.ToolButton {
                Layout.alignment: Qt.AlignVCenter
                icon.name: "overflow-menu"
                Accessible.name: qsTr("Environment actions")
                Controls.ToolTip.text: qsTr("Environment actions")
                enabled: !controller.busy && !controller.destroying && !controller.folderSharingBusy
                onClicked: environmentMenu.open()

                Controls.Menu {
                    id: environmentMenu

                    Controls.MenuItem {
                        text: qsTr("Destroy Fedora environment…")
                        icon.name: "edit-delete"
                        onTriggered: page.destroyRequested()
                    }
                }
            }
        }
    }

    Kirigami.Card {
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 250
        padding: 0
        background: null

        contentItem: ColumnLayout {
            spacing: Kirigami.Units.mediumSpacing

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Heading {
                    text: qsTr("Fedora 44 settings")
                    level: 3
                }

                Controls.Label {
                    text: qsTr("Choose which cubelinux folders this environment can access.")
                    opacity: 0.7
                    wrapMode: Text.Wrap
                }
            }

            Kirigami.Separator { Layout.fillWidth: true }

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
                    spacing: 0

                    Controls.Label {
                        text: qsTr("Home folder")
                        font.bold: true
                    }

                    Controls.Label {
                        text: qsTr("Shared automatically with Fedora.")
                        opacity: 0.7
                    }

                    Controls.Label {
                        text: qsTr("Your home folder is available at %1.").arg(controller.sharedHomePath)
                        opacity: 0.7
                    }
                }

                Controls.Label {
                    text: qsTr("Shared")
                    opacity: 0.7
                }
            }

            Kirigami.Separator { Layout.fillWidth: true }

            RowLayout {
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Controls.Label {
                        text: qsTr("Folder sharing")
                        font.bold: true
                    }

                    Controls.Label {
                        text: qsTr("Additional folders")
                        topPadding: Kirigami.Units.smallSpacing
                    }

                    Controls.Label {
                        visible: controller.sharedFolders.length === 0
                        text: qsTr("No additional folders shared.")
                        opacity: 0.7
                    }

                    Controls.ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(sharesColumn.implicitHeight, 220)
                        visible: controller.sharedFolders.length > 0
                        clip: true

                        ColumnLayout {
                            id: sharesColumn
                            width: parent.width
                            spacing: Kirigami.Units.smallSpacing

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
                                        spacing: 0

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
                                            opacity: modelData.available === "true" ? 0.7 : 1.0
                                            color: modelData.available === "true" ? Kirigami.Theme.textColor
                                                                                   : Kirigami.Theme.negativeTextColor
                                            elide: Text.ElideMiddle
                                        }
                                    }

                                    Controls.ToolButton {
                                        icon.name: "edit-delete"
                                        text: qsTr("Remove shared folder")
                                        enabled: !controller.busy && !controller.folderSharingBusy
                                                 && !controller.destroying
                                        onClicked: controller.removeSharedFolder(modelData.id)
                                    }
                                }
                            }
                        }
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

            Kirigami.Separator { Layout.fillWidth: true }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Heading {
                    text: qsTr("Port forwarding")
                    level: 4
                }

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("Fedora TCP services listening on its network interface at ports 1024 and above are forwarded to this host automatically.")
                    opacity: 0.7
                    wrapMode: Text.Wrap
                }

                Controls.Label {
                    Layout.fillWidth: true
                    visible: controller.forwardedPorts.length === 0
                    text: qsTr("No forwarded ports detected. Start a service in Fedora on a network interface to see it here.")
                    opacity: 0.7
                    wrapMode: Text.Wrap
                }

                Controls.ScrollView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(portRows.implicitHeight, 220)
                    visible: controller.forwardedPorts.length > 0
                    clip: true

                    ColumnLayout {
                        id: portRows
                        width: parent.width
                        spacing: Kirigami.Units.smallSpacing

                        Repeater {
                            model: controller.forwardedPorts

                            delegate: RowLayout {
                                required property var modelData

                                Layout.fillWidth: true
                                spacing: Kirigami.Units.mediumSpacing

                                Kirigami.Icon {
                                    source: "network-server"
                                    implicitWidth: Kirigami.Units.iconSizes.medium
                                    implicitHeight: Kirigami.Units.iconSizes.medium
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0

                                    Controls.Label {
                                        text: qsTr("TCP port %1 in Fedora").arg(modelData.port)
                                        font.bold: true
                                    }

                                    Controls.Label {
                                        text: modelData.status === "Forwarding"
                                              ? qsTr("Available on this host at %1").arg(modelData.hostAddress)
                                              : qsTr("Could not forward this port: %1").arg(modelData.error)
                                        opacity: modelData.status === "Forwarding" ? 0.7 : 1.0
                                        color: modelData.status === "Forwarding"
                                               ? Kirigami.Theme.textColor : Kirigami.Theme.negativeTextColor
                                        wrapMode: Text.Wrap
                                    }
                                }

                                Controls.CheckBox {
                                    text: qsTr("Expose to public")
                                    checked: modelData.publicAccess
                                    onToggled: controller.setPortPublicAccess(modelData.port, checked)

                                    Controls.ToolTip.text: qsTr("Bind this port to all host IPv4 interfaces. The host firewall still controls incoming connections.")
                                    Controls.ToolTip.visible: hovered
                                }
                            }
                        }
                    }
                }
            }

            Item { Layout.fillHeight: true }

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("Fedora can read and modify shared folders. If Fedora is running, it will restart when folder access changes.")
                opacity: 0.65
                wrapMode: Text.Wrap
            }
        }
    }

    Item { Layout.fillHeight: true }

    Controls.Label {
        Layout.leftMargin: Kirigami.Units.smallSpacing
        text: qsTr("Linux Subsystem")
        opacity: 0.55
    }
}
