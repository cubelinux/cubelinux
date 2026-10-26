import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("Virtual Shell Setup")
    width: 560
    height: 480
    minimumWidth: 480
    minimumHeight: 440
    visible: true

    pageStack.initialPage: Kirigami.ScrollablePage {
        title: qsTr("Virtual Shell Setup")
        padding: Kirigami.Units.largeSpacing

        Component.onCompleted: {
            if (setupController.ready)
                steps.currentIndex = 2
        }

        ColumnLayout {
            width: parent.width
            spacing: Kirigami.Units.largeSpacing

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.largeSpacing

                Kirigami.Icon {
                    source: "utilities-terminal"
                    Layout.preferredWidth: Kirigami.Units.iconSizes.huge
                    Layout.preferredHeight: Kirigami.Units.iconSizes.huge
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Kirigami.Heading {
                        Layout.fillWidth: true
                        text: qsTr("Set up your Linux shell")
                        level: 1
                        wrapMode: Text.Wrap
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("A few quick steps, then your workspace is ready.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }
                }
            }

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("Step %1 of 3").arg(steps.currentIndex + 1)
                opacity: 0.7
            }

            StackLayout {
                id: steps
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    spacing: Kirigami.Units.mediumSpacing

                    Kirigami.Heading {
                        Layout.fillWidth: true
                        text: qsTr("Welcome to Virtual Shell")
                        level: 2
                        wrapMode: Text.Wrap
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Virtual Shell gives you a separate Linux environment for terminal and development work. It runs in a container and does not replace your host system.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.mediumSpacing

                    Kirigami.Heading {
                        Layout.fillWidth: true
                        text: qsTr("Fedora, ready to use")
                        level: 2
                        wrapMode: Text.Wrap
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Virtual Shell uses Fedora. Your home folder is shared automatically, so your files are available in both Fedora and the host.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Programs running in Fedora can read and change files in your shared home folder.")
                        wrapMode: Text.Wrap
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.mediumSpacing

                    Kirigami.Heading {
                        Layout.fillWidth: true
                        text: setupController.ready ? qsTr("Your Fedora shell is ready") : qsTr("Ready to set up")
                        level: 2
                        wrapMode: Text.Wrap
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Linux environment: Fedora\nShared folder: your home folder")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        visible: !setupController.ready
                        text: qsTr("You may be asked to approve a one-time change to enable container networking.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        visible: setupController.busy
                        text: setupController.progressTitle
                        font.bold: true
                        wrapMode: Text.Wrap
                    }

                    Controls.ProgressBar {
                        Layout.fillWidth: true
                        visible: setupController.busy
                        indeterminate: true
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        visible: setupController.busy || setupController.progress.length > 0
                        text: setupController.progress
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true

                Controls.Button {
                    text: qsTr("Back")
                    visible: steps.currentIndex > 0
                    onClicked: steps.currentIndex -= 1
                }

                Item { Layout.fillWidth: true }

                Controls.Button {
                    text: qsTr("Next")
                    visible: steps.currentIndex < 2
                    highlighted: true
                    onClicked: steps.currentIndex += 1
                }

                Controls.Button {
                    text: setupController.ready ? qsTr("Open Virtual Shell") :
                        (setupController.busy ? qsTr("Setting up…") : qsTr("Set up Fedora"))
                    visible: steps.currentIndex === 2
                    enabled: !setupController.busy
                    highlighted: true
                    onClicked: {
                        if (setupController.ready)
                            setupController.openShell()
                        else
                            setupController.setup()
                    }
                }
            }
        }
    }
}
