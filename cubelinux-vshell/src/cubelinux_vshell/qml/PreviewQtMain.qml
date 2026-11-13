import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts

Controls.ApplicationWindow {
    id: root

    title: qsTr("cubelinux VShell UI Preview")
    width: 920
    height: 700
    minimumWidth: 760
    minimumHeight: 600
    visible: true
    property bool showingConfirmation: false

    SystemPalette {
        id: systemPalette
    }

    header: Controls.ToolBar {
        RowLayout {
            anchors.fill: parent
            spacing: 8

            Controls.ToolButton {
                visible: root.showingConfirmation
                text: "‹"
                Accessible.name: qsTr("Back")
                onClicked: root.showingConfirmation = false
            }

            Controls.Label {
                Layout.fillWidth: true
                text: qsTr("Set up cubelinux Runtime")
                font.bold: true
                elide: Text.ElideRight
            }

            Controls.Button {
                text: root.showingConfirmation ? qsTr("Set up Runtime") : qsTr("Next")
                icon.name: "go-next"
                onClicked: {
                    if (root.showingConfirmation) {
                        previewNotice.open()
                    } else {
                        root.showingConfirmation = true
                    }
                }
            }

            Controls.ToolButton {
                text: qsTr("Menu")
                onClicked: previewMenu.open()
            }
        }
    }

    Controls.Menu {
        id: previewMenu

        Controls.MenuItem {
            text: qsTr("About Linux Subsystem")
            onTriggered: previewNotice.open()
        }
    }

    StackLayout {
        anchors.fill: parent
        anchors.margins: 24
        currentIndex: root.showingConfirmation ? 1 : 0

        Controls.ScrollView {
            id: welcomeScroll

            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                id: welcomeContent

                width: welcomeScroll.availableWidth
                height: Math.max(welcomeScroll.availableHeight, welcomeContent.implicitHeight)
                spacing: 0

                Item {
                    Layout.fillHeight: true
                    Layout.minimumHeight: 24
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.maximumWidth: 680
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 40

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Image {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth: 88
                            Layout.preferredHeight: 88
                            source: previewIconUrl
                            sourceSize.width: 128
                            sourceSize.height: 128
                            fillMode: Image.PreserveAspectFit
                            Accessible.name: qsTr("cubelinux")
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            text: qsTr("Linux apps, at home on cubelinux")
                            font.pixelSize: 28
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.Wrap
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            text: qsTr("Set up cubelinux Runtime to run Linux apps and development tools alongside your desktop.")
                            opacity: 0.8
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.Wrap
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 18

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: systemPalette.mid
                            opacity: 0.5
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            text: qsTr("What you get")
                            font.pixelSize: 20
                            font.bold: true
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: welcomeScroll.availableWidth >= 680 ? 2 : 1
                            columnSpacing: 32
                            rowSpacing: 24

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                spacing: 14

                                Controls.Label {
                                    text: "▦"
                                    font.pixelSize: 30
                                    color: systemPalette.highlight
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Controls.Label {
                                        text: qsTr("Linux apps")
                                        font.bold: true
                                    }

                                    Controls.Label {
                                        Layout.fillWidth: true
                                        text: qsTr("Run graphical Linux apps alongside your cubelinux apps.")
                                        opacity: 0.75
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                spacing: 14

                                Controls.Label {
                                    text: ">_"
                                    font.pixelSize: 24
                                    color: systemPalette.highlight
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Controls.Label {
                                        text: qsTr("Development tools")
                                        font.bold: true
                                    }

                                    Controls.Label {
                                        Layout.fillWidth: true
                                        text: qsTr("Use the Runtime terminal for command-line tools and development.")
                                        opacity: 0.75
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    Layout.fillHeight: true
                    Layout.minimumHeight: 24
                }
            }
        }

        Controls.ScrollView {
            id: confirmScroll

            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                id: confirmContent

                width: confirmScroll.availableWidth
                height: Math.max(confirmScroll.availableHeight, confirmContent.implicitHeight)
                spacing: 0

                Item {
                    Layout.fillHeight: true
                    Layout.minimumHeight: 24
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.maximumWidth: 680
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 36

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Controls.Label {
                            Layout.fillWidth: true
                            text: qsTr("Before you begin")
                            font.pixelSize: 26
                            font.bold: true
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

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 16

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: systemPalette.mid
                            opacity: 0.5
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            text: qsTr("Setup details")
                            font.pixelSize: 20
                            font.bold: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: runtimeRow.implicitHeight + 32
                            radius: 8
                            color: systemPalette.base
                            border.color: systemPalette.mid

                            RowLayout {
                                id: runtimeRow
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 16

                                Image {
                                    Layout.preferredWidth: 56
                                    Layout.preferredHeight: 56
                                    source: previewIconUrl
                                    sourceSize.width: 128
                                    sourceSize.height: 128
                                    fillMode: Image.PreserveAspectFit
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

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

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: homeRow.implicitHeight + 32
                            radius: 8
                            color: systemPalette.base
                            border.color: systemPalette.mid

                            RowLayout {
                                id: homeRow
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 16

                                Controls.Label {
                                    text: "⌂"
                                    font.pixelSize: 34
                                    color: systemPalette.highlight
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Controls.Label {
                                        text: qsTr("Shared home folder")
                                        font.bold: true
                                    }

                                    Controls.Label {
                                        Layout.fillWidth: true
                                        text: qsTr("Runtime apps and the terminal can access your files at %1.").arg(previewController.sharedHomePath)
                                        opacity: 0.75
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            text: qsTr("Files in your shared home folder remain on cubelinux if you remove cubelinux Runtime. Other folders can be shared in settings.")
                            opacity: 0.75
                            wrapMode: Text.Wrap
                        }
                    }
                }

                Item {
                    Layout.fillHeight: true
                    Layout.minimumHeight: 24
                }
            }
        }
    }

    Controls.Dialog {
        id: previewNotice

        modal: true
        title: qsTr("Preview only")
        width: 440
        anchors.centerIn: parent
        standardButtons: Controls.Dialog.Ok

        contentItem: Controls.Label {
            text: qsTr("This prototype previews the interface. Setup and Runtime operations are not started.")
            wrapMode: Text.Wrap
        }
    }
}
