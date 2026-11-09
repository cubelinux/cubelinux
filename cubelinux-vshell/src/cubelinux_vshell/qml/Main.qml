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

    Component {
        id: aboutPage

        AboutApplicationPage {
            applicationName: qsTr("Linux Subsystem")
            productName: qsTr("Linux Subsystem")
            description: qsTr("Manage your CubeLinux Runtime environment.")
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

    Connections {
        target: setupController
        function onStateChanged() {
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
        title: qsTr("Linux environments")
        padding: 0

        actions: [
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
            currentIndex: 0

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
            running: true
            onTriggered: setupController.refreshStatus()
        }

        Kirigami.Dialog {
            id: destroyDialog

            modal: true
            title: qsTr("Reset Runtime environment?")
            width: Math.min(root.width - Kirigami.Units.largeSpacing * 2, 520)
            anchors.centerIn: parent
            padding: Kirigami.Units.largeSpacing
            showCloseButton: true
            standardButtons: Kirigami.Dialog.NoButton

            ColumnLayout {
                spacing: Kirigami.Units.mediumSpacing

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("This resets the Runtime system filesystem and container settings. Your shared home folder and user-installed Flatpak apps will remain. Runtime will be recreated from the image included with CubeLinux; no template download is needed.")
                    wrapMode: Text.Wrap
                }

                Controls.CheckBox {
                    id: destroyAcknowledged
                    Layout.fillWidth: true
                    text: qsTr("I understand this resets the Runtime system environment.")
                }
            }

            customFooterActions: [
                Kirigami.Action {
                    text: qsTr("Cancel")
                    icon.name: "dialog-cancel"
                    onTriggered: destroyDialog.close()
                },

                Kirigami.Action {
                    text: qsTr("Reset Runtime")
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
