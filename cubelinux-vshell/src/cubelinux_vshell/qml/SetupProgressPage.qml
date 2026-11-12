import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    property var controller
    property int displayedStepIndex: 0

    signal retryRequested()
    signal returnToOverviewRequested()
    signal aboutRequested()

    title: controller.setupFailed
           ? qsTr("Setup needs attention") : qsTr("Setting up Linux")

    onBackRequested: function(event) {
        if (controller.busy
                || (controller.ready && controller.setupFailed)) {
            event.accepted = true
        }
    }

    readonly property var setupSteps: [
        ({ title: qsTr("Preparing your account"), description: qsTr("Checking permissions and container mappings"), icon: "user-identity" }),
        ({ title: qsTr("Downloading the runtime"), description: qsTr("Getting the Fedora environment"), icon: "download" }),
        ({ title: qsTr("Creating your environment"), description: qsTr("Checking and unpacking the runtime image"), icon: "package-x-generic" }),
        ({ title: qsTr("Starting Fedora"), description: qsTr("Bringing up your Linux environment"), icon: "system-run" }),
        ({ title: qsTr("Connecting to the network"), description: qsTr("Waiting for Fedora to come online"), icon: "network-connect" }),
        ({ title: qsTr("Configuring Fedora"), description: qsTr("Preparing your guest account and network"), icon: "configure" }),
        ({ title: qsTr("Sharing your home folder"), description: qsTr("Connecting your files to Fedora"), icon: "folder-home" }),
        ({ title: qsTr("Connecting to your desktop"), description: qsTr("Preparing display and audio access"), icon: "video-display" }),
        ({ title: qsTr("Applying settings"), description: qsTr("Restarting Fedora and finishing setup"), icon: "view-refresh" })
    ]

    readonly property int activeStepIndex: {
        const title = controller.progressTitle.toLowerCase()
        if (title === "setup complete") return setupSteps.length
        if (title.indexOf("downloading cubelinux runtime") >= 0
                || title.indexOf("checking cubelinux runtime") >= 0) return 1
        if (title.indexOf("extracting cubelinux runtime") >= 0) return 2
        if (title.indexOf("starting fedora") >= 0) return 3
        if (title.indexOf("connecting fedora to the network") >= 0) return 4
        if (title.indexOf("preparing your fedora account") >= 0) return 5
        if (title.indexOf("sharing your home folder") >= 0) return 6
        if (title.indexOf("connecting fedora to your desktop") >= 0) return 7
        if (title.indexOf("restarting fedora") >= 0
                || title.indexOf("updating container settings") >= 0) return 8
        return 0
    }

    readonly property var displayedStep: setupSteps[
        Math.max(0, Math.min(displayedStepIndex, setupSteps.length - 1))
    ]

    readonly property bool showingComplete: displayedStepIndex >= setupSteps.length

    onActiveStepIndexChanged: {
        if (activeStepIndex === displayedStepIndex) {
            return
        }
        stepTransition.stop()
        if (!controller.busy) {
            displayedStepIndex = activeStepIndex
            stepContent.opacity = 1
            return
        }
        stepTransition.start()
    }

    Component.onCompleted: displayedStepIndex = activeStepIndex

    actions: [
        Kirigami.Action {
            text: qsTr("Try again")
            icon.name: "view-refresh"
            visible: !controller.busy && !controller.ready && controller.setupFailed
            onTriggered: page.retryRequested()
        },
        Kirigami.Action {
            text: qsTr("Return to overview")
            icon.name: "go-home"
            visible: !controller.busy && controller.ready && controller.setupFailed
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

    SequentialAnimation {
        id: stepTransition

        NumberAnimation {
            target: stepContent
            property: "opacity"
            to: 0
            duration: 150
            easing.type: Easing.InCubic
        }
        ScriptAction {
            script: page.displayedStepIndex = page.activeStepIndex
        }
        NumberAnimation {
            target: stepContent
            property: "opacity"
            to: 1
            duration: 180
            easing.type: Easing.OutCubic
        }
    }

    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing

        Item { Layout.fillHeight: true }

        Kirigami.Heading {
            Layout.fillWidth: true
            text: controller.setupFailed
                  ? qsTr("We couldn't finish setup")
                  : page.showingComplete
                    ? qsTr("Setup complete")
                    : qsTr("Setting up your Linux environment")
            level: 1
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
        }

        Controls.Label {
            Layout.fillWidth: true
            text: controller.setupFailed
                  ? qsTr("Review the message below, then retry setup or return to the overview.")
                  : page.showingComplete
                    ? qsTr("Fedora is ready to open from your desktop.")
                    : qsTr("This may take a few minutes. You can close this window; setup will continue in the background.")
            color: Kirigami.Theme.neutralTextColor
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
        }

        Item { Layout.preferredHeight: Kirigami.Units.largeSpacing }

        ColumnLayout {
            id: stepContent
            Layout.fillWidth: true
            spacing: Kirigami.Units.mediumSpacing
            opacity: 1
            visible: !page.showingComplete && !controller.setupFailed

            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 128
                Layout.preferredHeight: 128
                radius: width / 2
                color: Kirigami.Theme.alternateBackgroundColor

                Kirigami.Icon {
                    anchors.centerIn: parent
                    width: Kirigami.Units.iconSizes.huge
                    height: width
                    source: page.displayedStep.icon
                    color: Kirigami.Theme.highlightColor
                    Accessible.name: page.displayedStep.title
                }
            }

            Controls.ProgressBar {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: Kirigami.Units.gridUnit * 14
                Layout.maximumWidth: parent.width
                visible: controller.busy
                from: 0
                to: 100
                value: Math.max(0, controller.progressPercent)
                indeterminate: controller.progressPercent < 0
            }

            Controls.Label {
                Layout.alignment: Qt.AlignHCenter
                text: qsTr("STEP %1 OF %2")
                      .arg(page.displayedStepIndex + 1)
                      .arg(page.setupSteps.length)
                color: Kirigami.Theme.highlightColor
                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                font.weight: Font.DemiBold
                Accessible.name: text
            }

            Kirigami.Heading {
                Layout.fillWidth: true
                text: page.displayedStep.title
                level: 2
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }

            Controls.Label {
                Layout.fillWidth: true
                text: page.displayedStep.description
                color: Kirigami.Theme.neutralTextColor
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }

            Controls.Label {
                Layout.alignment: Qt.AlignHCenter
                visible: controller.progressPercent >= 0
                text: qsTr("%1% complete in this step").arg(controller.progressPercent)
                color: Kirigami.Theme.neutralTextColor
                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.mediumSpacing
            visible: page.showingComplete && !controller.setupFailed

            Kirigami.Icon {
                Layout.alignment: Qt.AlignHCenter
                implicitWidth: Kirigami.Units.iconSizes.huge
                implicitHeight: implicitWidth
                source: "dialog-ok-apply"
                color: Kirigami.Theme.positiveTextColor
            }
            Kirigami.Heading {
                Layout.fillWidth: true
                text: qsTr("Your Linux environment is ready")
                level: 2
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

        Item { Layout.fillHeight: true }
    }
}
