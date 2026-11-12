import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("Linux Subsystem")
    width: 920
    height: 700
    minimumWidth: 760
    minimumHeight: 600
    visible: true
    property bool closeAfterSetup: false

    Timer {
        id: setupCompletionTimer
        interval: 1100
        repeat: false
        onTriggered: {
            if (setupController.setupComplete && !root.closeAfterSetup) {
                root.pageStack.layers.clear()
            }
        }
    }

    pageStack.globalToolBar.showNavigationButtons: setupController.busy
        || root.pageStack.layers.busy ? 0
        : Kirigami.ApplicationHeaderStyle.ShowBackButton

    onClosing: function(close) {
        if (setupController.busy || setupController.folderSharingBusy) {
            close.accepted = false
            closeAfterSetup = true
            root.hide()
        } else {
            Qt.callLater(Qt.quit)
        }
    }

    Component {
        id: aboutPage

        AboutApplicationPage {
            applicationName: qsTr("Linux Subsystem")
            productName: qsTr("Linux Subsystem")
            description: qsTr("Manage your cubelinux Runtime environment, powered by Fedora Linux.")
            version: softwareVersion
            homepage: "https://cubelinux.github.io"
            bugAddress: "https://github.com/cubelinux/cubelinux/issues"
            copyrightStatement: "Copyright © 2026 VIREAK KEOSOKVIBOL <vireakvibol@gmail.com>"
            components: JSON.parse(aboutComponentsJson)
        }
    }

    Component {
        id: environmentSettingsPage

        EnvironmentSettingsPage {
            controller: setupController
            onReturnToWorkspaceRequested: root.pageStack.pop()
            onAboutRequested: root.pageStack.layers.push(aboutPage)
        }
    }

    Component {
        id: setupProgressPage

        SetupProgressPage {
            controller: setupController
            onRetryRequested: setupController.setup()
            onReturnToOverviewRequested: root.pageStack.layers.clear()
            onAboutRequested: root.pageStack.layers.push(aboutPage)
        }
    }

    Component {
        id: setupConfirmPage

        SetupConfirmPage {
            controller: setupController
            navigationBusy: root.pageStack.layers.busy
            onSetupRequested: {
                if (!root.pageStack.layers.busy
                        && !setupController.busy
                        && !setupController.ready
                        && setupController.connectivityStatus === "online") {
                    root.pageStack.layers.push(setupProgressPage)
                    setupController.setup()
                }
            }
            onAboutRequested: root.pageStack.layers.push(aboutPage)
        }
    }

    Connections {
        target: setupController
        function onStateChanged() {
            if (setupController.ready && setupController.setupComplete) {
                setupCompletionTimer.start()
            }
            root.finishDeferredClose()
        }
        function onFolderSharingChanged() {
            root.finishDeferredClose()
        }
    }

    function finishDeferredClose() {
        if (!closeAfterSetup || setupController.busy || setupController.folderSharingBusy) {
            return
        }
        closeAfterSetup = false
        if (setupController.setupFailed || setupController.destroyFailed) {
            root.showNormal()
            root.raise()
            root.requestActivate()
        } else {
            Qt.callLater(Qt.quit)
        }
    }

    pageStack.initialPage: Kirigami.Page {
        id: homePage
        title: setupController.ready ? qsTr("Linux environments") : qsTr("Set up Linux")
        padding: 0

        actions: [
            Kirigami.Action {
                text: qsTr("Next")
                icon.name: "go-next"
                visible: !setupController.ready
                enabled: !setupController.busy && !root.pageStack.layers.busy
                onTriggered: {
                    if (!setupController.ready
                            && !root.pageStack.layers.busy) {
                        root.pageStack.layers.push(setupConfirmPage)
                    }
                }
            },
            Kirigami.Action {
                text: qsTr("Menu")
                icon.name: "application-menu"
                children: [
                    Kirigami.Action {
                        text: qsTr("About Linux Subsystem")
                        icon.name: "help-about"
                        onTriggered: root.pageStack.layers.push(aboutPage)
                    }
                ]
            }
        ]

        StackLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            currentIndex: setupController.ready ? 1 : 0

            SetupWelcomePage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }

            WorkspacePage {
                Layout.fillWidth: true
                Layout.fillHeight: true
                controller: setupController
                onDestroyRequested: destroyDialog.open()
                onSettingsRequested: root.pageStack.push(environmentSettingsPage)
            }
        }

        Timer {
            interval: 2500
            repeat: true
            running: setupController.ready
            onTriggered: setupController.refreshStatus()
        }

        Kirigami.Dialog {
            id: destroyDialog

            modal: true
            title: qsTr("Destroy cubelinux Runtime?")
            width: Math.min(root.width - Kirigami.Units.largeSpacing * 2, 520)
            anchors.centerIn: parent
            padding: Kirigami.Units.largeSpacing
            showCloseButton: true
            standardButtons: Kirigami.Dialog.NoButton

            ColumnLayout {
                spacing: Kirigami.Units.mediumSpacing

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("This permanently destroys cubelinux Runtime. It deletes installed apps, container settings, and files stored in the Fedora filesystem. Your shared cubelinux home folder will remain untouched. You can create a new environment later from this setup wizard. Creating it again downloads the current cubelinux Runtime image from GHCR and requires an internet connection. This cannot be undone.")
                    wrapMode: Text.Wrap
                }

                Controls.CheckBox {
                    id: destroyAcknowledged
                    Layout.fillWidth: true
                    text: qsTr("I understand this permanently destroys cubelinux Runtime.")
                }
            }

            customFooterActions: [
                Kirigami.Action {
                    text: qsTr("Cancel")
                    icon.name: "dialog-cancel"
                    onTriggered: destroyDialog.close()
                },

                Kirigami.Action {
                    text: qsTr("Destroy environment")
                    icon.name: "edit-delete"
                    enabled: destroyAcknowledged.checked && !setupController.busy
                    onTriggered: {
                        destroyAcknowledged.checked = false
                        setupController.destroyContainer()
                        destroyDialog.close()
                    }
                }
            ]

            onClosed: destroyAcknowledged.checked = false
        }

        Component.onCompleted: setupController.refreshStatus()
    }
}
