import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts

ColumnLayout {
    id: root

    property string currentChannel: "Stable"

    spacing: 8

    Controls.Frame {
        Layout.fillWidth: true

        RowLayout {
            spacing: 12

            Controls.Label {
                text: "⇄"
                font.pixelSize: 24
                opacity: 0.8
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("Update channel")
                    font.weight: Font.DemiBold
                }

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("%1 · Recommended for most people").arg(root.currentChannel)
                    opacity: 0.75
                    wrapMode: Text.Wrap
                }
            }

            Controls.Button {
                text: qsTr("Change")
                onClicked: channelDialog.open()
            }
        }
    }

    Controls.Dialog {
        id: channelDialog

        property string selectedChannel: root.currentChannel

        title: qsTr("Choose an update channel")
        modal: true
        width: 440
        standardButtons: Controls.Dialog.Close

        onOpened: selectedChannel = root.currentChannel

        contentItem: ColumnLayout {
            spacing: 12

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("Choose how early you want to receive cubelinux updates.")
                wrapMode: Text.Wrap
            }

            Repeater {
                model: [
                    {
                        name: qsTr("Stable"),
                        details: qsTr("Recommended for everyday use. Updates are tested first.")
                    },
                    {
                        name: qsTr("Beta"),
                        details: qsTr("Try upcoming changes before they reach Stable.")
                    },
                    {
                        name: qsTr("Unstable"),
                        details: qsTr("Get the newest changes. Issues are more likely.")
                    }
                ]

                delegate: RowLayout {
                    required property var modelData

                    Layout.fillWidth: true
                    spacing: 8

                    Controls.RadioButton {
                        checked: channelDialog.selectedChannel === modelData.name
                        onClicked: channelDialog.selectedChannel = modelData.name
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Controls.Label {
                            Layout.fillWidth: true
                            text: modelData.name
                            font.weight: Font.DemiBold
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            text: modelData.details
                            opacity: 0.75
                            wrapMode: Text.Wrap
                        }
                    }

                    Controls.Label {
                        visible: modelData.name === root.currentChannel
                        text: qsTr("Current")
                        opacity: 0.7
                    }
                }
            }

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("Prototype only. Channel switching is not connected yet.")
                opacity: 0.7
                wrapMode: Text.Wrap
            }

            Controls.Button {
                Layout.alignment: Qt.AlignRight
                text: qsTr("Switch to %1").arg(channelDialog.selectedChannel)
                enabled: false
            }
        }
    }
}
