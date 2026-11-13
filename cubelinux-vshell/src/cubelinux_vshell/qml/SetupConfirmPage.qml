import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    property var controller
    property bool navigationBusy: false
    property url logoSource: "cubelinux-icon.png"
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
        id: content

        width: page.availableWidth
        height: Math.max(page.availableHeight, content.implicitHeight)
        spacing: 0

        Item {
            Layout.fillHeight: true
            Layout.minimumHeight: Kirigami.Units.largeSpacing
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 42
            Layout.alignment: Qt.AlignHCenter
            spacing: Kirigami.Units.largeSpacing * 1.5

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.mediumSpacing

                Kirigami.Heading {
                    Layout.fillWidth: true
                    text: qsTr("Before you begin")
                    level: 1
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                }

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("Set up cubelinux Runtime for Linux apps and development tools. An internet connection is needed for the initial download.")
                    opacity: 0.8
                    horizontalAlignment: Text.AlignHCenter
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

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.mediumSpacing

                Kirigami.Separator {
                    Layout.fillWidth: true
                }

                Kirigami.Heading {
                    Layout.fillWidth: true
                    text: qsTr("Setup details")
                    level: 2
                }

                Kirigami.Card {
                    Layout.fillWidth: true

                    contentItem: RowLayout {
                        spacing: Kirigami.Units.mediumSpacing

                        Image {
                            source: page.logoSource
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
                                text: qsTr("A separate environment for your Linux apps, tools, and settings.")
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
                                text: qsTr("Shared home folder")
                                font.bold: true
                            }

                            Controls.Label {
                                Layout.fillWidth: true
                                text: qsTr("Runtime apps and the terminal can access your files at %1.").arg(page.controller.sharedHomePath)
                                opacity: 0.75
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }

                Kirigami.InlineMessage {
                    Layout.fillWidth: true
                    showCloseButton: false
                    type: Kirigami.MessageType.Information
                    text: qsTr("Files in your shared home folder remain on cubelinux if you remove cubelinux Runtime. Other folders can be shared in settings.")
                }
            }
        }

        Item {
            Layout.fillHeight: true
            Layout.minimumHeight: Kirigami.Units.largeSpacing
        }
    }

    Component.onCompleted: page.controller.checkInternet()
}
