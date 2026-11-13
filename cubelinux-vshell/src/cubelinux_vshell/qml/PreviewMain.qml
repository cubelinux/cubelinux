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

    Component {
        id: confirmPage

        SetupConfirmPage {
            controller: previewController
            navigationBusy: root.pageStack.layers.busy
            logoSource: previewIconUrl
            onSetupRequested: previewNotice.open()
            onAboutRequested: previewNotice.open()
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
            text: qsTr("This prototype previews the interface. Setup and Runtime operations are not started.")
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
