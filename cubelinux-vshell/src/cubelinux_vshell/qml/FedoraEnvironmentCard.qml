import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Card {
    id: card

    property var controller
    visible: controller.ready || controller.fedoraReady || controller.fedoraBusy
             || controller.fedoraSetupFailed
    Layout.fillWidth: true
    Layout.preferredHeight: controller.fedoraBusy || controller.fedoraSetupFailed ? 164 : 96
    Layout.minimumHeight: controller.fedoraBusy || controller.fedoraSetupFailed ? 164 : 96

    contentItem: ColumnLayout {
        spacing: Kirigami.Units.smallSpacing

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.mediumSpacing

            Image {
                source: "fedora-icon.svg"
                sourceSize.width: 128
                sourceSize.height: 128
                fillMode: Image.PreserveAspectFit
                smooth: true
                Layout.preferredWidth: 64
                Layout.preferredHeight: Kirigami.Units.iconSizes.large
                Accessible.name: qsTr("Fedora logo")
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Heading {
                    text: qsTr("Fedora environment")
                    level: 2
                }

                Controls.Label {
                    text: qsTr("Fedora Linux · read-only system · Flatpak")
                    opacity: 0.7
                }
            }

            Kirigami.Icon {
                source: card.controller.fedoraBusy
                        ? "view-refresh"
                        : card.controller.fedoraContainerStatus === "running"
                          ? "media-playback-start"
                          : card.controller.fedoraReady
                            ? "media-playback-stop" : "list-add"
                color: card.controller.fedoraBusy
                       ? Kirigami.Theme.neutralTextColor
                       : card.controller.fedoraContainerStatus === "running"
                         ? Kirigami.Theme.positiveTextColor
                         : card.controller.fedoraReady
                           ? Kirigami.Theme.negativeTextColor
                           : Kirigami.Theme.neutralTextColor
                implicitWidth: Kirigami.Units.iconSizes.medium
                implicitHeight: Kirigami.Units.iconSizes.medium
                Accessible.name: card.controller.fedoraBusy
                                 ? qsTr("Creating Fedora environment")
                                 : card.controller.fedoraContainerStatus
                                   === "running" ? qsTr("Running")
                                   : card.controller.fedoraReady ? qsTr("Stopped")
                                   : qsTr("Not created")

                RotationAnimation on rotation {
                    from: 0
                    to: 360
                    duration: 1000
                    loops: Animation.Infinite
                    running: card.controller.fedoraBusy
                    onRunningChanged: if (!running) card.rotation = 0
                }
            }

            Controls.Button {
                text: card.controller.fedoraReady
                      ? qsTr("Open Fedora terminal")
                      : card.controller.fedoraSetupFailed
                        ? qsTr("Try again") : qsTr("Create Fedora container")
                icon.name: card.controller.fedoraReady
                           ? "utilities-terminal" : "list-add"
                highlighted: !card.controller.fedoraReady
                enabled: card.controller.ready && !card.controller.busy
                         && !card.controller.fedoraBusy
                         && !card.controller.folderSharingBusy
                         && !card.controller.destroying
                onClicked: card.controller.fedoraReady
                           ? card.controller.openFedoraShell()
                           : card.controller.createFedoraContainer()
            }
        }

        Controls.ProgressBar {
            Layout.fillWidth: true
            visible: card.controller.fedoraBusy
            indeterminate: true
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: card.controller.fedoraBusy || card.controller.fedoraSetupFailed
            text: card.controller.fedoraProgress
            type: card.controller.fedoraSetupFailed
                  ? Kirigami.MessageType.Error : Kirigami.MessageType.Information
        }
    }
}
