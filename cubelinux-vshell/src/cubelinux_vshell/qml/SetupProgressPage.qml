import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    property var controller
    signal retryRequested()
    signal returnToOverviewRequested()
    signal aboutRequested()
    title: controller.setupFailed
           ? qsTr("Setup needs attention") : qsTr("Setting up Linux")
    onBackRequested: function(event) {
        if (controller.busy
                || (controller.ready
                    && controller.setupFailed)) {
            event.accepted = true
        }
    }

    actions: [
        Kirigami.Action {
            text: qsTr("Try again")
            icon.name: "view-refresh"
            visible: !controller.busy && !controller.ready
                     && controller.setupFailed
            onTriggered: page.retryRequested()
        },
        Kirigami.Action {
            text: qsTr("Return to overview")
            icon.name: "go-home"
            visible: !controller.busy && controller.ready
                     && controller.setupFailed
            onTriggered: page.returnToOverviewRequested()
        },
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

    readonly property var setupStages: [
        qsTr("Preparing your account"),
        qsTr("Downloading cubelinux Runtime"),
        qsTr("Creating your environment"),
        qsTr("Connecting Linux to your desktop")
    ]
    readonly property int activeSetupStage: {
        const title = controller.progressTitle.toLowerCase()
        if (title === "setup complete") return setupStages.length
        if (title.indexOf("preparing your account") >= 0
                || title.indexOf("container networking") >= 0) return 0
        if (title.indexOf("download") >= 0
                || title.indexOf("checking for cubelinux runtime") >= 0
                || title.indexOf("checking cubelinux runtime") >= 0
                || title.indexOf("extracting cubelinux runtime") >= 0) return 1
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
            text: controller.ready && controller.setupFailed
                  ? qsTr("The Fedora environment was created, but desktop setup did not finish. Return to the overview, then destroy and recreate Fedora to try again.\n\n%1").arg(controller.progress)
                  : controller.progress
            type: controller.setupFailed
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
