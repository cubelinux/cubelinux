import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("Setup Terminal")
    width: 920
    height: 700
    minimumWidth: 760
    minimumHeight: 600
    visible: true
    property bool closeAfterSetup: false

    onClosing: function(close) {
        if (setupController.busy) {
            close.accepted = false
            closeAfterSetup = true
            root.hide()
        } else {
            Qt.callLater(Qt.quit)
        }
    }

    property int wizardStep: 0
    readonly property string containerStatusLabel: setupController.resetting
                                                     ? qsTr("Resetting Fedora")
                                                     : setupController.containerStatus === "running"
                                                       ? qsTr("Running") : qsTr("Stopped")
    readonly property string containerStatusIcon: setupController.resetting
                                                    ? "view-refresh"
                                                    : setupController.containerStatus === "running"
                                                      ? "media-playback-start" : "media-playback-stop"
    readonly property color containerStatusColor: setupController.resetting
                                                    ? Kirigami.Theme.neutralTextColor
                                                    : setupController.containerStatus === "running"
                                                      ? Kirigami.Theme.positiveTextColor
                                                      : Kirigami.Theme.negativeTextColor

    globalDrawer: Kirigami.GlobalDrawer {
        isMenu: true
        actions: [
            Kirigami.Action {
                text: qsTr("About Setup Terminal")
                icon.name: "help-about"
                onTriggered: root.pageStack.layers.push(aboutPage)
            }
        ]
    }

    Component {
        id: aboutPage

        Kirigami.AboutPage {
            aboutData: {
                "displayName": qsTr("Setup Terminal"),
                "productName": qsTr("CubeLinux VShell"),
                "componentName": "cubelinux-vshell",
                "shortDescription": qsTr("Manage your Fedora Linux environment."),
                "homepage": "https://github.com/cubelinux/cubelinux-vshell",
                "bugAddress": "",
                "version": softwareVersion,
                "otherText": "",
                "authors": [],
                "credits": [],
                "translators": [],
                "licenses": [],
                "copyrightStatement": "",
                "desktopFileName": "org.cubelinux.VShell"
            }
            getInvolvedUrl: "https://github.com/cubelinux/cubelinux-vshell"
        }
    }

    Connections {
        target: setupController
        function onStateChanged() {
            if (root.closeAfterSetup && !setupController.busy) {
                root.closeAfterSetup = false
                if (setupController.progressTitle === qsTr("Setup failed")
                        || setupController.progressTitle === qsTr("Reset failed")) {
                    root.showNormal()
                    root.raise()
                    root.requestActivate()
                } else {
                    Qt.callLater(Qt.quit)
                }
            }
        }
    }

    pageStack.initialPage: Kirigami.Page {
        title: qsTr("Setup Terminal")
        padding: Kirigami.Units.largeSpacing

        ColumnLayout {
            anchors.fill: parent
            spacing: Kirigami.Units.largeSpacing

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: setupController.ready ? 1 : 0

                // First-run setup flow
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: Kirigami.Units.largeSpacing

                        RowLayout {
                            Layout.fillWidth: true

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.smallSpacing

                                Kirigami.Heading {
                                    text: qsTr("Setup Terminal")
                                    level: 1
                                }

                                Controls.Label {
                                    text: qsTr("A Fedora workspace for your tools and development work.")
                                    opacity: 0.75
                                    wrapMode: Text.Wrap
                                }
                            }

                            Controls.Label {
                                text: qsTr("STEP %1 OF 3").arg(wizardStep + 1)
                                font.bold: true
                                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                                opacity: 0.7
                            }
                        }

                        Controls.ProgressBar {
                            Layout.fillWidth: true
                            from: 0
                            to: 3
                            value: wizardStep + 1
                        }

                        StackLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            currentIndex: wizardStep

                            // Step 1: choose the supplied Linux environment
                            ColumnLayout {
                                Layout.alignment: Qt.AlignTop
                                spacing: Kirigami.Units.largeSpacing

                                Controls.Label {
                                    text: qsTr("LINUX ENVIRONMENT")
                                    font.bold: true
                                    font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                                    opacity: 0.7
                                }

                                Kirigami.Card {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 112

                                    contentItem: RowLayout {
                                        spacing: Kirigami.Units.largeSpacing

                                        Kirigami.Icon {
                                            source: "utilities-terminal"
                                            Layout.preferredWidth: Kirigami.Units.iconSizes.large
                                            Layout.preferredHeight: Kirigami.Units.iconSizes.large
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: Kirigami.Units.smallSpacing

                                            Kirigami.Heading {
                                                text: qsTr("Fedora Linux")
                                                level: 3
                                            }

                                            Controls.Label {
                                                text: qsTr("Fedora 44 · Default environment")
                                                opacity: 0.7
                                            }
                                        }

                                        Kirigami.Icon {
                                            source: "go-next"
                                            Layout.preferredWidth: Kirigami.Units.iconSizes.small
                                            Layout.preferredHeight: Kirigami.Units.iconSizes.small
                                            opacity: 0.65
                                        }
                                    }
                                }

                                Controls.Label {
                                    Layout.fillWidth: true
                                    text: qsTr("A separate Linux environment that works alongside cubelinux.")
                                    opacity: 0.75
                                    wrapMode: Text.Wrap
                                }

                                Item { Layout.fillHeight: true }
                            }

                            // Step 2: confirm sharing and the default environment name
                            ColumnLayout {
                                Layout.alignment: Qt.AlignTop
                                spacing: Kirigami.Units.largeSpacing

                                Kirigami.Heading {
                                    text: qsTr("Ready to set up")
                                    level: 2
                                }

                                Controls.Label {
                                    text: qsTr("Your environment will be called cubelinux.")
                                    opacity: 0.75
                                    wrapMode: Text.Wrap
                                }

                                Kirigami.Card {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 76

                                    contentItem: RowLayout {
                                        spacing: Kirigami.Units.mediumSpacing

                                        Kirigami.Icon {
                                            source: "folder-home"
                                            Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                                            Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: Kirigami.Units.smallSpacing

                                            Controls.Label {
                                                text: qsTr("Home folder shared")
                                                font.bold: true
                                            }

                                            Controls.Label {
                                                text: qsTr("Your files are available in both systems.")
                                                opacity: 0.7
                                                wrapMode: Text.Wrap
                                            }
                                        }
                                    }
                                }

                                Item { Layout.fillHeight: true }
                            }

                            // Step 3: show setup progress and recoverable errors
                            ColumnLayout {
                                Layout.alignment: Qt.AlignTop
                                spacing: Kirigami.Units.largeSpacing

                                Kirigami.Heading {
                                    Layout.fillWidth: true
                                    text: setupController.busy
                                          ? setupController.progressTitle
                                          : (setupController.progressTitle === qsTr("Setup failed")
                                             ? qsTr("Setup needs attention")
                                             : qsTr("Ready to set up"))
                                    level: 2
                                    wrapMode: Text.Wrap
                                }

                                Kirigami.InlineMessage {
                                    Layout.fillWidth: true
                                    visible: setupController.busy || setupController.progress.length > 0
                                    text: setupController.progress
                                    type: setupController.progressTitle === qsTr("Setup failed")
                                          ? Kirigami.MessageType.Error
                                          : Kirigami.MessageType.Information
                                }

                                Controls.ProgressBar {
                                    Layout.fillWidth: true
                                    visible: setupController.busy
                                    from: 0
                                    to: 100
                                    value: Math.max(0, setupController.progressPercent)
                                    indeterminate: setupController.progressPercent < 0
                                }

                                Item { Layout.fillHeight: true }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true

                            Item { Layout.fillWidth: true }

                            Controls.Button {
                                text: qsTr("Back")
                                visible: wizardStep > 0 && wizardStep < 2 && !setupController.busy
                                onClicked: wizardStep -= 1
                            }

                            Controls.Button {
                                visible: wizardStep < 2
                                text: qsTr("Next")
                                highlighted: true
                                onClicked: wizardStep += 1
                            }

                            Controls.Button {
                                visible: wizardStep === 2 && !setupController.busy
                                highlighted: true
                                text: setupController.progressTitle === qsTr("Setup failed")
                                      ? qsTr("Try again") : qsTr("Set up")
                                onClicked: setupController.setup()
                            }
                        }
                    }
                }

                // Manager home after setup, preserving the current left navigation
                // and workspace card placement.
                RowLayout {
                    spacing: Kirigami.Units.largeSpacing

                    Kirigami.Card {
                        Layout.preferredWidth: 190
                        Layout.fillHeight: true

                        contentItem: ColumnLayout {
                            spacing: Kirigami.Units.largeSpacing

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.mediumSpacing

                                Kirigami.Icon {
                                    source: "utilities-terminal"
                                    Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                                    Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                                }

                                ColumnLayout {
                                    spacing: 0

                                    Controls.Label {
                                        text: qsTr("Setup Terminal")
                                        font.bold: true
                                    }
                                }
                            }

                            Item { Layout.fillHeight: true }

                            RowLayout {
                                spacing: Kirigami.Units.smallSpacing

                                Item {
                                    Layout.preferredWidth: Kirigami.Units.iconSizes.small
                                    Layout.preferredHeight: Kirigami.Units.iconSizes.small

                                    Kirigami.Icon {
                                        id: sidebarStatusIcon
                                        anchors.fill: parent
                                        source: root.containerStatusIcon
                                        color: root.containerStatusColor
                                        Accessible.name: root.containerStatusLabel

                                        RotationAnimation on rotation {
                                            from: 0
                                            to: 360
                                            duration: 1000
                                            loops: Animation.Infinite
                                            running: setupController.resetting
                                            onRunningChanged: {
                                                if (!running) sidebarStatusIcon.rotation = 0
                                            }
                                        }
                                    }

                                    Controls.ToolTip.visible: statusHover.containsMouse
                                    Controls.ToolTip.text: root.containerStatusLabel

                                    MouseArea {
                                        id: statusHover
                                        anchors.fill: parent
                                        acceptedButtons: Qt.NoButton
                                        hoverEnabled: true
                                    }
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Kirigami.Units.largeSpacing

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Controls.Label {
                                text: qsTr("YOUR WORKSPACE")
                                font.bold: true
                                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                                opacity: 0.65
                            }

                            Kirigami.Heading {
                                text: qsTr("Your workspace")
                                level: 1
                            }

                            Controls.Label {
                                text: qsTr("Your Linux tools, in one place.")
                                opacity: 0.7
                            }
                        }

                        Kirigami.InlineMessage {
                            Layout.fillWidth: true
                            visible: setupController.busy
                                     || setupController.progressTitle === qsTr("Reset failed")
                            text: setupController.progress
                            type: setupController.progressTitle === qsTr("Reset failed")
                                  ? Kirigami.MessageType.Error : Kirigami.MessageType.Information
                        }

                        Controls.ProgressBar {
                            Layout.fillWidth: true
                            visible: setupController.busy
                            indeterminate: true
                        }

                        Kirigami.Card {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 380
                            padding: Kirigami.Units.mediumSpacing

                            contentItem: ColumnLayout {
                                spacing: Kirigami.Units.mediumSpacing

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.largeSpacing

                                    Kirigami.Icon {
                                        source: "utilities-terminal"
                                        Layout.preferredWidth: Kirigami.Units.iconSizes.large
                                        Layout.preferredHeight: Kirigami.Units.iconSizes.large
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: Kirigami.Units.smallSpacing

                                        Kirigami.Heading {
                                            text: qsTr("cubelinux")
                                            level: 2
                                        }

                                        Controls.Label {
                                            text: qsTr("Fedora 44 · Default environment")
                                            opacity: 0.7
                                        }
                                    }

                                    Item {
                                        Layout.preferredWidth: Kirigami.Units.iconSizes.small
                                        Layout.preferredHeight: Kirigami.Units.iconSizes.small

                                        Kirigami.Icon {
                                            id: workspaceStatusIcon
                                            anchors.fill: parent
                                            source: root.containerStatusIcon
                                            color: root.containerStatusColor
                                            Accessible.name: root.containerStatusLabel

                                            RotationAnimation on rotation {
                                                from: 0
                                                to: 360
                                                duration: 1000
                                                loops: Animation.Infinite
                                                running: setupController.resetting
                                                onRunningChanged: {
                                                    if (!running) workspaceStatusIcon.rotation = 0
                                                }
                                            }
                                        }

                                        Controls.ToolTip.visible: workspaceStatusHover.containsMouse
                                        Controls.ToolTip.text: root.containerStatusLabel

                                        MouseArea {
                                            id: workspaceStatusHover
                                            anchors.fill: parent
                                            acceptedButtons: Qt.NoButton
                                            hoverEnabled: true
                                        }
                                    }
                                }

                                Kirigami.Separator {
                                    Layout.fillWidth: true
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.mediumSpacing

                                    Kirigami.Icon {
                                        source: "folder-home"
                                        Layout.preferredWidth: Kirigami.Units.iconSizes.small
                                        Layout.preferredHeight: Kirigami.Units.iconSizes.small
                                    }

                                    ColumnLayout {
                                        spacing: 0

                                        Controls.Label {
                                            text: qsTr("Home folder shared")
                                            font.bold: true
                                        }

                                        Controls.Label {
                                            text: qsTr("Your files are available inside Fedora.")
                                            opacity: 0.7
                                        }
                                    }

                                    Item { Layout.fillWidth: true }
                                }

                                Item { Layout.fillHeight: true }

                                Controls.Button {
                                    Layout.fillWidth: true
                                    text: qsTr("Open terminal")
                                    icon.name: "utilities-terminal"
                                    highlighted: true
                                    enabled: !setupController.busy
                                             && !setupController.resetting
                                             && !resetDialog.visible
                                    onClicked: setupController.openShell()
                                }

                                Controls.Button {
                                    Layout.fillWidth: true
                                    text: qsTr("Reset Fedora environment…")
                                    icon.name: "edit-delete"
                                    enabled: !setupController.busy
                                             && !setupController.resetting
                                             && !resetDialog.visible
                                    onClicked: resetDialog.open()
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }

        Timer {
            interval: 2500
            repeat: true
            running: setupController.ready
            onTriggered: setupController.refreshStatus()
        }

        Controls.Dialog {
            id: resetDialog

            modal: true
            title: qsTr("Reset Fedora environment?")
            width: Math.min(root.width - Kirigami.Units.largeSpacing * 2, 520)
            anchors.centerIn: parent

            contentItem: ColumnLayout {
                spacing: Kirigami.Units.mediumSpacing

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("This permanently deletes the Fedora container, including installed apps, container settings, and files stored inside its filesystem. VShell will check whether a newer Fedora 44 LXC template is available, download it if needed, and otherwise reuse the cached template. If the update check fails, VShell will try the cached template. If recreating the container fails, you may need to run setup again. This cannot be undone.")
                    wrapMode: Text.Wrap
                }

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("Your shared home folder is stored on cubelinux and will remain untouched.")
                    wrapMode: Text.Wrap
                    font.bold: true
                }

                Controls.CheckBox {
                    id: resetAcknowledged
                    Layout.fillWidth: true
                    text: qsTr("I understand this permanently deletes the Fedora environment.")
                }
            }

            footer: RowLayout {
                spacing: Kirigami.Units.mediumSpacing

                Item { Layout.fillWidth: true }

                Controls.Button {
                    text: qsTr("Cancel")
                    onClicked: resetDialog.close()
                }

                Controls.Button {
                    text: qsTr("Delete and reset")
                    icon.name: "edit-delete"
                    enabled: resetAcknowledged.checked && !setupController.busy
                    onClicked: {
                        resetAcknowledged.checked = false
                        setupController.resetContainer()
                        resetDialog.close()
                    }
                }
            }

            onClosed: resetAcknowledged.checked = false
        }

        Component.onCompleted: setupController.refreshStatus()
    }
}
