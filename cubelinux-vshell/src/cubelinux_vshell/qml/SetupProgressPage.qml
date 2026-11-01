import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    property var controller
    signal retryRequested()
    title: controller.progressTitle === qsTr("Setup failed")
           ? qsTr("Setup needs attention") : qsTr("Setting up Linux")
    onBackRequested: function(event) {
        if (controller.busy) {
            event.accepted = true
        }
    }

    actions: [
        Kirigami.Action {
            text: qsTr("Try again")
            icon.name: "view-refresh"
            visible: !controller.busy && controller.progressTitle === qsTr("Setup failed")
            onTriggered: page.retryRequested()
        }
    ]

    readonly property var setupStages: [
        qsTr("Preparing your account"),
        qsTr("Downloading Fedora"),
        qsTr("Creating your environment"),
        qsTr("Connecting Linux to your desktop")
    ]
    readonly property int activeSetupStage: {
        const title = controller.progressTitle.toLowerCase()
        if (title === "setup complete") return setupStages.length
        if (title.indexOf("preparing your account") >= 0
                || title.indexOf("container networking") >= 0) return 0
        if (title.indexOf("download") >= 0
                || title.indexOf("checking for fedora") >= 0
                || title.indexOf("checking the fedora image") >= 0
                || title.indexOf("extracting fedora") >= 0
                || title.indexOf("cached fedora image") >= 0) return 1
        if (title.indexOf("desktop session") >= 0
                || title.indexOf("restarting fedora") >= 0) return 3
        return 2
    }

    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Controls.BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                running: controller.busy
                visible: running
            }

            Kirigami.Heading {
                Layout.fillWidth: true
                text: page.title
                level: 1
                horizontalAlignment: Text.AlignHCenter
            }

            Controls.Label {
                Layout.fillWidth: true
                visible: controller.busy
                text: qsTr("This can take a few minutes. You can close this window; setup will continue in the background.")
                opacity: 0.75
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !controller.busy && controller.progress.length > 0
            text: controller.progress
            type: controller.progressTitle === qsTr("Setup failed")
                  ? Kirigami.MessageType.Error : Kirigami.MessageType.Information
        }

        Controls.ProgressBar {
            Layout.fillWidth: true
            visible: controller.busy
            from: 0
            to: 100
            value: Math.max(0, controller.progressPercent)
            indeterminate: controller.progressPercent < 0
        }

        Repeater {
            model: page.setupStages

            delegate: RowLayout {
                required property int index
                required property string modelData

                Layout.fillWidth: true
                spacing: Kirigami.Units.mediumSpacing

                Kirigami.Icon {
                    source: index < page.activeSetupStage
                            ? "emblem-checked"
                            : index === page.activeSetupStage
                              ? "media-playback-start" : "media-playback-stop"
                    color: index < page.activeSetupStage
                           ? Kirigami.Theme.positiveTextColor
                           : index === page.activeSetupStage
                             ? Kirigami.Theme.textColor : Kirigami.Theme.neutralTextColor
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: Kirigami.Units.iconSizes.small
                    Accessible.name: modelData
                }

                Controls.Label {
                    Layout.fillWidth: true
                    text: modelData
                    font.bold: index === page.activeSetupStage
                    opacity: index > page.activeSetupStage ? 0.55 : 1.0
                    wrapMode: Text.Wrap
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
