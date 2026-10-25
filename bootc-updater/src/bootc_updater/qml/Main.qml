import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("bootc Updater")
    width: 720
    height: 520
    minimumWidth: 480
    minimumHeight: 420

    pageStack.initialPage: Kirigami.Page {
        title: qsTr("System updates")

        ColumnLayout {
            anchors.fill: parent
            spacing: Kirigami.Units.largeSpacing

            Kirigami.Heading {
                Layout.fillWidth: true
                text: qsTr("System image")
                level: 1
            }

            Kirigami.Card {
                Layout.fillWidth: true

                contentItem: ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing

                    Kirigami.Heading {
                        Layout.fillWidth: true
                        text: qsTr("Update status is not connected yet")
                        level: 3
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("The updater interface is ready. Bootc status checks and update staging will be connected next.")
                        wrapMode: Text.Wrap
                    }
                }
            }

            Item {
                Layout.fillHeight: true
            }

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("Updates will be staged as a new image and take effect after reboot.")
                opacity: 0.75
                wrapMode: Text.Wrap
            }
        }
    }
}
