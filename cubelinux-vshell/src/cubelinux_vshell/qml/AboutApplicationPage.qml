import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    property string applicationName: ""
    property string productName: ""
    property string description: ""
    property string version: ""
    property string homepage: ""
    property string bugAddress: ""
    property string copyrightStatement: ""
    property var components: []

    title: qsTr("About %1").arg(applicationName)

    ColumnLayout {
        width: page.width
        spacing: Kirigami.Units.largeSpacing

        Controls.TabBar {
            id: tabs
            Layout.fillWidth: true

            Controls.TabButton { text: qsTr("About") }
            Controls.TabButton { text: qsTr("Authors") }
            Controls.TabButton { text: qsTr("Credits") }
            Controls.TabButton { text: qsTr("License") }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            ColumnLayout {
                spacing: Kirigami.Units.mediumSpacing
                Kirigami.Heading {
                    Layout.fillWidth: true
                    text: page.productName
                    level: 1
                    wrapMode: Text.Wrap
                }
                Controls.Label {
                    Layout.fillWidth: true
                    text: page.description
                    wrapMode: Text.Wrap
                }
                Controls.Label {
                    text: qsTr("Version %1").arg(page.version)
                }
                Controls.Label {
                    Layout.fillWidth: true
                    text: page.copyrightStatement
                    wrapMode: Text.Wrap
                }
                Controls.Label {
                    text: qsTr("<a href=\"%1\">Project website</a>").arg(page.homepage)
                    onLinkActivated: function(link) { Qt.openUrlExternally(link) }
                }
                Controls.Label {
                    text: qsTr("<a href=\"%1\">Report a bug</a>").arg(page.bugAddress)
                    onLinkActivated: function(link) { Qt.openUrlExternally(link) }
                }
            }

            ColumnLayout {
                spacing: Kirigami.Units.mediumSpacing
                Kirigami.Heading { text: qsTr("Authors"); level: 2 }
                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("VIREAK KEOSOKVIBOL — Author")
                    wrapMode: Text.Wrap
                }
                Controls.Label {
                    text: "<a href=\"mailto:vireakvibol@gmail.com\">vireakvibol@gmail.com</a>"
                    onLinkActivated: function(link) { Qt.openUrlExternally(link) }
                }
            }

            ColumnLayout {
                spacing: Kirigami.Units.mediumSpacing
                Kirigami.Heading { text: qsTr("Runtime components"); level: 2 }
                Repeater {
                    model: page.components
                    delegate: Controls.Label {
                        required property var modelData
                        Layout.fillWidth: true
                        text: qsTr("%1 — %2").arg(modelData.name).arg(modelData.version)
                        wrapMode: Text.Wrap
                    }
                }
            }

            ColumnLayout {
                spacing: Kirigami.Units.mediumSpacing
                Kirigami.Heading { text: qsTr("License"); level: 2 }
                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("This application is free software licensed under the GNU General Public License, version 3 or (at your option) any later version.")
                    wrapMode: Text.Wrap
                }
                Controls.Label {
                    text: "<a href=\"https://www.gnu.org/licenses/gpl-3.0.txt\">GNU GPL version 3 license text</a>"
                    onLinkActivated: function(link) { Qt.openUrlExternally(link) }
                }
                Controls.Label { text: "SPDX: GPL-3.0-or-later" }
            }
        }
    }
}
