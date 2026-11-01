import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Controls.ScrollView {
    id: page

    property var controller
    property bool darkTheme: false
    signal destroyRequested()
    signal settingsRequested()
    contentWidth: availableWidth
    clip: true

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

    ColumnLayout {
        width: page.availableWidth
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
                    enabled: !controller.busy && !controller.destroying
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
                            text: qsTr("Environment settings")
                            icon.name: "configure"
                            onTriggered: page.settingsRequested()
                        }

                        Controls.MenuItem {
                            text: qsTr("Destroy Fedora environment…")
                            icon.name: "edit-delete"
                            onTriggered: page.destroyRequested()
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Kirigami.Units.largeSpacing
        }
    }
}
