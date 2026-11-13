import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Card {
    id: card

    property string environmentId
    property string environmentName
    property string environmentDetails
    property bool isDefault: false
    property string statusLabel
    property string statusIcon
    property color statusColor: Kirigami.Theme.textColor
    property bool operationBusy: false
    property bool canOpen: true
    property bool canManage: true
    property url logoSource: "cubelinux-icon.png"

    signal openRequested(string environmentId)
    signal settingsRequested(string environmentId, string environmentName)
    signal destroyRequested(string environmentId)

    contentItem: ColumnLayout {
        spacing: Kirigami.Units.mediumSpacing

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.mediumSpacing

            Image {
                source: card.logoSource
                sourceSize.width: 128
                sourceSize.height: 128
                fillMode: Image.PreserveAspectFit
                smooth: true
                Layout.preferredWidth: 64
                Layout.preferredHeight: 64
                Accessible.name: qsTr("cubelinux")
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                RowLayout {
                    spacing: Kirigami.Units.mediumSpacing

                    Kirigami.Heading {
                        text: card.environmentName
                        level: 2
                    }

                    Controls.Label {
                        visible: card.isDefault
                        text: qsTr("DEFAULT")
                        font.bold: true
                        font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                        opacity: 0.7
                    }
                }

                Controls.Label {
                    text: card.environmentDetails
                    opacity: 0.75
                }
            }

            RowLayout {
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Icon {
                    id: statusIconItem
                    source: card.statusIcon
                    color: card.statusColor
                    implicitWidth: Kirigami.Units.iconSizes.medium
                    implicitHeight: Kirigami.Units.iconSizes.medium
                    Accessible.name: card.statusLabel

                    RotationAnimation on rotation {
                        from: 0
                        to: 360
                        duration: 1000
                        loops: Animation.Infinite
                        running: card.operationBusy
                        onRunningChanged: if (!running) statusIconItem.rotation = 0
                    }
                }

                Controls.Label {
                    text: card.statusLabel
                    color: card.statusColor
                    font.bold: true
                }
            }
        }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.mediumSpacing

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("Your apps and tools are ready to use.")
                opacity: 0.75
                wrapMode: Text.Wrap
            }

            Controls.Button {
                text: qsTr("Open terminal")
                icon.name: "utilities-terminal"
                highlighted: true
                enabled: card.canOpen
                onClicked: card.openRequested(card.environmentId)
            }

            Controls.ToolButton {
                icon.name: "overflow-menu"
                Accessible.name: qsTr("Environment actions")
                Controls.ToolTip.text: qsTr("Environment actions")
                enabled: card.canManage
                onClicked: environmentMenu.open()

                Controls.Menu {
                    id: environmentMenu

                    Controls.MenuItem {
                        text: qsTr("Environment settings")
                        icon.name: "configure"
                        onTriggered: card.settingsRequested(card.environmentId, card.environmentName)
                    }

                    Controls.MenuItem {
                        text: qsTr("Destroy cubelinux Runtime…")
                        icon.name: "edit-delete"
                        onTriggered: card.destroyRequested(card.environmentId)
                    }
                }
            }
        }
    }
}
