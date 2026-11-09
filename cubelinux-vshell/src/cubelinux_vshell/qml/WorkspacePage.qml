import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Controls.ScrollView {
    id: page

    property var controller
    signal destroyRequested()
    signal settingsRequested()
    contentWidth: availableWidth
    clip: true

    readonly property string containerStatusLabel: controller.destroying
        ? qsTr("Resetting Runtime")
        : controller.busy && !controller.ready
          ? qsTr("Preparing Runtime")
        : controller.folderSharingBusy
          ? qsTr("Updating folder access")
          : controller.setupFailed ? qsTr("Setup failed")
          : controller.containerStatus === "running" ? qsTr("Running") : qsTr("Stopped")
    readonly property string containerStatusIcon: controller.destroying || controller.folderSharingBusy
        || (controller.busy && !controller.ready)
        ? "view-refresh"
        : controller.containerStatus === "running" ? "media-playback-start" : "media-playback-stop"
    readonly property color containerStatusColor: controller.destroying || controller.folderSharingBusy
        || (controller.busy && !controller.ready)
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
                     || controller.setupFailed
                     || controller.destroyFailed
            text: controller.progress
            type: controller.setupFailed || controller.destroyFailed
                  ? Kirigami.MessageType.Error : Kirigami.MessageType.Information
        }

        Controls.Button {
            Layout.alignment: Qt.AlignLeft
            visible: controller.setupFailed
            text: qsTr("Try again")
            icon.name: "view-refresh"
            onClicked: controller.setup()
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
            Layout.preferredHeight: page.availableWidth < 560 ? 156 : 96
            Layout.minimumHeight: page.availableWidth < 560 ? 156 : 96

            contentItem: GridLayout {
                columns: page.availableWidth < 560 ? 3 : 5
                rowSpacing: Kirigami.Units.smallSpacing
                columnSpacing: Kirigami.Units.mediumSpacing

                Image {
                    source: "fedora-icon.svg"
                    sourceSize.width: 128
                    sourceSize.height: 128
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    Layout.preferredWidth: 64
                    Layout.preferredHeight: Kirigami.Units.iconSizes.large
                    Layout.alignment: Qt.AlignVCenter
                    Layout.row: 0
                    Layout.column: 0
                }

                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Layout.alignment: Qt.AlignVCenter
                    Layout.fillWidth: true
                    Layout.row: 0
                    Layout.column: 1

                    RowLayout {
                        spacing: Kirigami.Units.mediumSpacing

                        Kirigami.Heading {
                            text: qsTr("CubeLinux Runtime")
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
                        text: qsTr("Fedora Linux · immutable system · Flatpak")
                        opacity: 0.7
                    }
                }

                Item {
                    Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                    Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                    Layout.alignment: Qt.AlignVCenter
                    Layout.row: 0
                    Layout.column: 2

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
                                     || (controller.busy && !controller.ready)
                            onRunningChanged: if (!running) statusIcon.rotation = 0
                        }
                    }
                }

                Controls.Button {
                    Layout.alignment: Qt.AlignVCenter
                    Layout.row: page.availableWidth < 560 ? 1 : 0
                    Layout.column: page.availableWidth < 560 ? 0 : 3
                    Layout.columnSpan: page.availableWidth < 560 ? 2 : 1
                    Layout.fillWidth: page.availableWidth < 560
                    text: qsTr("Open Runtime terminal")
                    icon.name: "utilities-terminal"
                    highlighted: true
                    enabled: !controller.busy && !controller.destroying
                             && !controller.folderSharingBusy
                             && !controller.setupFailed
                    onClicked: controller.openShell()
                }

                Controls.ToolButton {
                    Layout.alignment: Qt.AlignVCenter
                    Layout.row: page.availableWidth < 560 ? 1 : 0
                    Layout.column: page.availableWidth < 560 ? 2 : 4
                    icon.name: "overflow-menu"
                    Accessible.name: qsTr("Runtime actions")
                    Controls.ToolTip.text: qsTr("Runtime actions")
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
                            text: qsTr("Reset Runtime…")
                            icon.name: "view-refresh"
                            enabled: controller.ready || controller.destroyFailed
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
