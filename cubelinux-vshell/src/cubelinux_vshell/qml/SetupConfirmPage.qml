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
    title: qsTr("Set up Fedora®")

    actions: [
        Kirigami.Action {
            text: qsTr("Set up Linux")
            icon.name: "go-next"
            enabled: !page.controller.busy && !page.controller.ready
                     && !page.navigationBusy
            onTriggered: {
                if (enabled) {
                    page.setupRequested()
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
                text: qsTr("Linux Subsystem will create Fedora 44 as your Linux environment.")
                opacity: 0.75
                wrapMode: Text.Wrap
            }
        }

        Kirigami.Card {
            Layout.fillWidth: true

            contentItem: RowLayout {
                spacing: Kirigami.Units.mediumSpacing

                Image {
                    source: "fedora-icon.svg"
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
                        text: qsTr("Fedora® Linux 44")
                        font.bold: true
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Installed apps and data stay in Fedora.")
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
            text: qsTr("Your shared home files stay on cubelinux if you destroy Fedora.")
            opacity: 0.75
            wrapMode: Text.Wrap
        }
    }
}
