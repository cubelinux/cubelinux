import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("Set up Virtual Shell")
    width: 720
    height: 640
    minimumWidth: 560
    minimumHeight: 560
    visible: true

    pageStack.initialPage: Kirigami.ScrollablePage {
        title: qsTr("Virtual Shell")
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
                        text: qsTr("Your Linux workspace")
                        level: 1
                        wrapMode: Text.Wrap
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Set up a separate Linux environment for terminal work and development.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: setupLayout.implicitHeight + Kirigami.Units.largeSpacing * 2
                radius: Kirigami.Units.mediumSpacing
                color: Kirigami.Theme.backgroundColor
                border.color: Kirigami.Theme.separatorColor

                ColumnLayout {
                    id: setupLayout
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.largeSpacing
                    spacing: Kirigami.Units.mediumSpacing

                    Kirigami.Heading {
                        text: qsTr("Choose a Linux environment")
                        level: 2
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("The first version will use a standard LXC system image. You can install tools inside it without changing the host system image.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }

                    Controls.ComboBox {
                        id: distroChoice
                        Layout.fillWidth: true
                        model: ["Fedora", "Debian", "Ubuntu"]
                        currentIndex: 0
                        displayText: qsTr("%1 (LXC system image)").arg(currentText)
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    Kirigami.Heading {
                        text: qsTr("Project folder")
                        level: 2
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Choose the folder you want to use from both the host and the Linux environment.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }

                    Controls.TextField {
                        id: projectPath
                        Layout.fillWidth: true
                        placeholderText: qsTr("For example: /home/you/Projects")
                        text: ""
                    }

                    Kirigami.Separator { Layout.fillWidth: true }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("This uses a Linux container that shares the host kernel. It is a separate workspace, not a virtual machine.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("OCI registry images are not directly supported as LXC system images. Start with a distro image; OCI import can be added later.")
                        wrapMode: Text.Wrap
                    }

                    Controls.Button {
                        Layout.fillWidth: true
                        text: qsTr("Create Virtual Shell")
                        icon.name: "dialog-ok-apply"
                        enabled: false
                        highlighted: true
                        Controls.ToolTip.visible: hovered
                        Controls.ToolTip.text: qsTr("Container setup will be enabled when the LXC backend is ready.")
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Setup is not connected yet. This screen is the initial UI prototype.")
                        horizontalAlignment: Text.AlignHCenter
                        opacity: 0.65
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}
