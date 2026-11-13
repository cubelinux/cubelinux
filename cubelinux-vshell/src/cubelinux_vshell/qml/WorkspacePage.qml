import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Controls.ScrollView {
    id: page

    property var controller
    property url logoSource: "cubelinux-icon.png"
    // The current controller has one Runtime; card delegates can consume a future list model.
    readonly property var environments: [
        ({ id: "vshell", name: qsTr("cubelinux Runtime"), details: qsTr("cubelinux Runtime · x86_64"), isDefault: true })
    ]
    signal destroyRequested(string environmentId)
    signal settingsRequested(string environmentId, string environmentName)

    contentWidth: availableWidth
    clip: true

    readonly property string containerStatusLabel: controller.destroying
        ? qsTr("Destroying cubelinux Runtime")
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

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Heading {
                    Layout.fillWidth: true
                    text: qsTr("Linux environments")
                    level: 1
                }

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("Open and manage your cubelinux Runtime environment.")
                    opacity: 0.75
                    wrapMode: Text.Wrap
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

            Repeater {
                model: page.environments

                delegate: EnvironmentCard {
                    required property var modelData

                    Layout.fillWidth: true
                    environmentId: modelData.id
                    environmentName: modelData.name
                    environmentDetails: modelData.details
                    isDefault: modelData.isDefault
                    logoSource: page.logoSource
                    statusLabel: page.containerStatusLabel
                    statusIcon: page.containerStatusIcon
                    statusColor: page.containerStatusColor
                    operationBusy: controller.destroying || controller.folderSharingBusy
                    canOpen: !controller.busy && !controller.destroying
                             && !controller.folderSharingBusy && !controller.setupFailed
                    canManage: !controller.busy && !controller.destroying
                               && !controller.folderSharingBusy
                    onOpenRequested: controller.openShell()
                    onSettingsRequested: page.settingsRequested(modelData.id, modelData.name)
                    onDestroyRequested: page.destroyRequested(modelData.id)
                }
            }
        }

        Item {
            Layout.fillHeight: true
            Layout.minimumHeight: Kirigami.Units.largeSpacing
        }
    }
}
