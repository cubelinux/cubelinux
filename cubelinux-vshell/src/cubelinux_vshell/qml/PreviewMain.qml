import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("cubelinux VShell UI Preview")
    width: 920
    height: 700
    minimumWidth: 760
    minimumHeight: 600
    visible: true
    property string selectedEnvironmentId: "vshell"
    property string selectedEnvironmentName: qsTr("cubelinux Runtime")
    property string previewMessage: qsTr("This prototype previews the interface. Setup and Runtime operations are not started.")

    Connections {
        target: previewController
        function onPreviewActionRequested(action) {
            root.previewMessage = qsTr("%1 is not available in this preview.").arg(action)
            previewNotice.open()
        }
    }

    Component {
        id: confirmPage

        SetupConfirmPage {
            controller: previewController
            navigationBusy: root.pageStack.layers.busy
            logoSource: previewIconUrl
            onSetupRequested: {
                root.previewMessage = qsTr("Runtime setup is not started in this preview.")
                previewNotice.open()
            }
            onAboutRequested: {
                root.previewMessage = qsTr("About information is not part of this UI preview.")
                previewNotice.open()
            }
        }
    }

    Component {
        id: workspacePreviewPage

        Kirigami.Page {
            title: qsTr("Linux environments")
            padding: 0

            WorkspacePage {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.largeSpacing
                controller: previewController
                logoSource: previewIconUrl
                onSettingsRequested: function(environmentId, environmentName) {
                    root.selectedEnvironmentId = environmentId
                    root.selectedEnvironmentName = environmentName
                    root.pageStack.layers.push(settingsPreviewPage)
                }
                onDestroyRequested: function(environmentId) {
                    root.selectedEnvironmentId = environmentId
                    root.previewMessage = qsTr("Destroying cubelinux Runtime is disabled in this preview.")
                    previewNotice.open()
                }
            }
        }
    }

    Component {
        id: settingsPreviewPage

        EnvironmentSettingsPage {
            controller: previewController
            environmentId: root.selectedEnvironmentId
            environmentName: root.selectedEnvironmentName
            onReturnToWorkspaceRequested: root.pageStack.layers.pop()
            onAboutRequested: {
                root.previewMessage = qsTr("About information is not part of this UI preview.")
                previewNotice.open()
            }
        }
    }

    pageStack.initialPage: Kirigami.Page {
        title: qsTr("Set up cubelinux Runtime")
        padding: 0

        actions: [
            Kirigami.Action {
                text: qsTr("Next")
                icon.name: "go-next"
                onTriggered: root.pageStack.layers.push(confirmPage)
            },
            Kirigami.Action {
                text: qsTr("Menu")
                icon.name: "application-menu"
                children: [
                    Kirigami.Action {
                        text: qsTr("Preview environment overview")
                        icon.name: "computer"
                        onTriggered: root.pageStack.layers.push(workspacePreviewPage)
                    },
                    Kirigami.Action {
                        text: qsTr("About Linux Subsystem")
                        icon.name: "help-about"
                        onTriggered: previewNotice.open()
                    }
                ]
            }
        ]

        SetupWelcomePage {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            logoSource: previewIconUrl
        }
    }

    Kirigami.Dialog {
        id: previewNotice

        modal: true
        title: qsTr("Preview only")
        width: Math.min(root.width - Kirigami.Units.largeSpacing * 2, 440)
        anchors.centerIn: parent
        padding: Kirigami.Units.largeSpacing
        showCloseButton: true
        standardButtons: Kirigami.Dialog.NoButton

        Controls.Label {
            Layout.fillWidth: true
            text: root.previewMessage
            wrapMode: Text.Wrap
        }

        customFooterActions: [
            Kirigami.Action {
                text: qsTr("Close")
                icon.name: "dialog-close"
                onTriggered: previewNotice.close()
            }
        ]
    }
}
