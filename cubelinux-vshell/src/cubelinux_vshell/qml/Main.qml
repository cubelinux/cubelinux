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

    globalDrawer: Kirigami.GlobalDrawer {
        isMenu: true
        actions: [
            Kirigami.Action {
                text: qsTr("About Linux Subsystem")
                icon.name: "help-about"
                onTriggered: root.pageStack.layers.push(aboutPage)
            }
        ]
    }

    Component {
        id: aboutPage

        Kirigami.AboutPage {
            aboutData: {
                "displayName": qsTr("Linux Subsystem"),
                "productName": qsTr("Linux Subsystem"),
                "componentName": "cubelinux-vshell",
                "shortDescription": qsTr("Manage your Fedora Linux environment."),
                "homepage": "https://github.com/cubelinux/cubelinux",
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
            getInvolvedUrl: "https://github.com/cubelinux/cubelinux"
        }
    }

    Component {
        id: environmentSettingsPage

        EnvironmentSettingsPage {
            controller: setupController
        }
    }

    Component {
        id: setupProgressPage

        SetupProgressPage {
            controller: setupController
            onRetryRequested: setupController.setup()
            onReturnToOverviewRequested: root.pageStack.layers.clear()
        }
    }

    Component {
        id: setupConfirmPage

        SetupConfirmPage {
            controller: setupController
            navigationBusy: root.pageStack.layers.busy
            darkTheme: root.palette.window.hslLightness < 0.5
            onSetupRequested: {
                if (!root.pageStack.layers.busy
                        && !setupController.busy
                        && !setupController.ready) {
                    root.pageStack.layers.push(setupProgressPage)
                    setupController.setup()
                }
            }
        }
    }

    Connections {
        target: setupController
        function onStateChanged() {
            if (setupController.ready && setupController.setupComplete) {
                root.pageStack.layers.clear()
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
            }
        ]

        StackLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            currentIndex: setupController.ready ? 1 : 0

            SetupWelcomePage {
                Layout.fillWidth: true
                Layout.fillHeight: true
                darkTheme: root.palette.window.hslLightness < 0.5
            }

            WorkspacePage {
                Layout.fillWidth: true
                Layout.fillHeight: true
                controller: setupController
                darkTheme: root.palette.window.hslLightness < 0.5
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
            title: qsTr("Destroy Fedora environment?")
            width: Math.min(root.width - Kirigami.Units.largeSpacing * 2, 520)
            anchors.centerIn: parent
            padding: Kirigami.Units.largeSpacing
            showCloseButton: true
            standardButtons: Kirigami.Dialog.NoButton

            ColumnLayout {
                spacing: Kirigami.Units.mediumSpacing

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("This permanently destroys the Fedora environment. It deletes installed apps, container settings, and files stored in the Fedora filesystem. Your shared cubelinux home folder will remain untouched. You can create a new Fedora environment later from this setup wizard. Linux Subsystem will reuse the cached Fedora image when available. This cannot be undone.")
                    wrapMode: Text.Wrap
                }

                Controls.CheckBox {
                    id: destroyAcknowledged
                    Layout.fillWidth: true
                    text: qsTr("I understand this permanently destroys the Fedora environment.")
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
