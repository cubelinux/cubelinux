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
                        text: qsTr("Virtual Shell will use the Fedora LXC image. Your home folder will be shared automatically, so your files are available in both Fedora and the host.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }
                }

                ColumnLayout {
                    spacing: Kirigami.Units.mediumSpacing

                    Kirigami.Heading {
                        Layout.fillWidth: true
                        text: qsTr("Everything is ready")
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
                        text: qsTr("You can start using Virtual Shell after setup finishes.")
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
                    text: qsTr("Set up Fedora")
                    visible: steps.currentIndex === 2
                    enabled: false
                    highlighted: true
                    Controls.ToolTip.visible: hovered
                    Controls.ToolTip.text: qsTr("Setup will be available when the LXC backend is ready.")
                }
            }

            Controls.Label {
                Layout.fillWidth: true
                visible: steps.currentIndex === 2
                text: qsTr("Container setup is not connected yet.")
                horizontalAlignment: Text.AlignHCenter
                opacity: 0.65
                wrapMode: Text.Wrap
            }
        }
    }
}
