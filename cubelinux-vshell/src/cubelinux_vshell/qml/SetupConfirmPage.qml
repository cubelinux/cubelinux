import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    property var controller
    property bool navigationBusy: false
    signal setupRequested()
    signal aboutRequested()
    title: qsTr("Set up cubelinux Runtime")

    actions: [
        Kirigami.Action {
            text: qsTr("Set up Linux")
            icon.name: "go-next"
            enabled: !page.controller.busy && !page.controller.ready
                     && !page.navigationBusy
                     && page.controller.connectivityStatus === "online"
            onTriggered: {
                if (enabled) {
                    page.setupRequested()
                }
            }
        },
        Kirigami.Action {
            text: page.controller.connectivityStatus === "checking"
                  ? qsTr("Checking connection…")
                  : page.controller.connectivityStatus === "offline"
                    ? qsTr("Retry connection check") : qsTr("Check connection")
            icon.name: page.controller.connectivityStatus === "checking"
                       ? "network-wired" : "view-refresh"
            visible: page.controller.connectivityStatus !== "online"
            enabled: page.controller.connectivityStatus !== "checking"
            onTriggered: page.controller.checkInternet()
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

    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Heading {
                text: qsTr("Before you begin")
                level: 1
            }

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("Linux Subsystem will create cubelinux Runtime, based on Fedora Linux 44. An internet connection is required to download it.")
                opacity: 0.75
                wrapMode: Text.Wrap
            }
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: page.controller.connectivityStatus !== "online"
            showCloseButton: false
            type: page.controller.connectivityStatus === "offline"
                  ? Kirigami.MessageType.Error : Kirigami.MessageType.Information
            text: page.controller.connectivityStatus === "checking"
                  ? qsTr("Checking access to the cubelinux Runtime registry…")
                  : page.controller.connectivityStatus === "offline"
                    ? qsTr("The cubelinux Runtime registry could not be reached. Connect to the internet and retry before starting setup.\n\nDetails: %1").arg(page.controller.connectivityError)
                    : qsTr("Checking that the cubelinux Runtime registry is reachable…")
        }

        Kirigami.Card {
            Layout.fillWidth: true

            contentItem: RowLayout {
                spacing: Kirigami.Units.mediumSpacing

                Image {
                    source: "cubelinux-icon.svg"
                    sourceSize.width: 128
                    sourceSize.height: 128
                    fillMode: Image.PreserveAspectFit
                    Layout.preferredWidth: 56
                    Layout.preferredHeight: Kirigami.Units.iconSizes.large
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Controls.Label {
                        text: qsTr("cubelinux Runtime")
                        font.bold: true
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Fedora Linux 44 powers this environment. Installed apps and data stay here.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }
                }
            }
        }

        Kirigami.Card {
            Layout.fillWidth: true

            contentItem: RowLayout {
                spacing: Kirigami.Units.mediumSpacing

                Kirigami.Icon {
                    source: "folder-home"
                    implicitWidth: Kirigami.Units.iconSizes.medium
                    implicitHeight: Kirigami.Units.iconSizes.medium
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Controls.Label {
                        text: qsTr("Home folder shared")
                        font.bold: true
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Your files are available at %1 in Fedora. Other folders can be added later in settings.").arg(controller.sharedHomePath)
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }
                }
            }
        }

        Controls.Label {
            Layout.fillWidth: true
            text: qsTr("Your shared home files stay on cubelinux if you destroy cubelinux Runtime.")
            opacity: 0.75
            wrapMode: Text.Wrap
        }
    }

    Component.onCompleted: page.controller.checkInternet()
}
