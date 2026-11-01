import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Controls.ScrollView {
    id: page

    property bool darkTheme: false
    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        width: page.availableWidth
        spacing: Kirigami.Units.largeSpacing

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing

            Image {
                source: page.darkTheme
                        ? "file:///usr/share/fedora-logos/fedora_logo_darkbackground.svg"
                        : "file:///usr/share/fedora-logos/fedora_logo.svg"
                sourceSize.width: 144
                sourceSize.height: 96
                fillMode: Image.PreserveAspectFit
                Layout.preferredWidth: 88
                Layout.preferredHeight: 64
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("Create a Fedora environment for Linux apps and development tools.")
                    opacity: 0.75
                    wrapMode: Text.Wrap
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.mediumSpacing

            Kirigami.Heading {
                text: qsTr("What you get")
                level: 2
            }

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("Linux apps alongside your cubelinux apps")
                wrapMode: Text.Wrap
            }

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("A Fedora terminal for command-line tools")
                wrapMode: Text.Wrap
            }
        }

    }
}
