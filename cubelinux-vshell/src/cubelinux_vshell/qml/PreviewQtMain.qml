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
    property int previewPageIndex: 0
    property string previewMessage: qsTr("This prototype previews the interface. Setup and Runtime operations are not started.")

    SystemPalette {
        id: systemPalette
    }

    Connections {
        target: previewController
        function onPreviewActionRequested(action) {
            root.previewMessage = qsTr("%1 is not available in this preview.").arg(action)
            previewNotice.open()
        }
    }

    header: Controls.ToolBar {
        RowLayout {
            anchors.fill: parent
            spacing: 8

            Controls.ToolButton {
                visible: root.previewPageIndex > 0
                text: "‹"
                Accessible.name: qsTr("Back")
                onClicked: root.previewPageIndex = root.previewPageIndex === 3 ? 2 : 0
            }

            Controls.Label {
                Layout.fillWidth: true
                text: root.previewPageIndex < 2
                      ? qsTr("Set up cubelinux Runtime")
                      : root.previewPageIndex === 2
                        ? qsTr("Linux environments") : qsTr("Environment settings")
                font.bold: true
                elide: Text.ElideRight
            }

            Controls.Button {
                text: root.previewPageIndex === 0 ? qsTr("Next")
                      : root.previewPageIndex === 1 ? qsTr("Set up Runtime")
                      : root.previewPageIndex === 2 ? qsTr("Environment settings")
                                                    : qsTr("Back to environments")
                icon.name: "go-next"
                onClicked: {
                    if (root.previewPageIndex === 0) {
                        root.previewPageIndex = 1
                    } else if (root.previewPageIndex === 1) {
                        root.previewMessage = qsTr("Runtime setup is not started in this preview.")
                        previewNotice.open()
                    } else if (root.previewPageIndex === 2) {
                        root.previewPageIndex = 3
                    } else {
                        root.previewPageIndex = 2
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
            text: qsTr("Welcome page")
            onTriggered: root.previewPageIndex = 0
        }

        Controls.MenuItem {
            text: qsTr("Setup details")
            onTriggered: root.previewPageIndex = 1
        }

        Controls.MenuSeparator {}

        Controls.MenuItem {
            text: qsTr("Environment overview")
            onTriggered: root.previewPageIndex = 2
        }

        Controls.MenuItem {
            text: qsTr("Environment settings")
            onTriggered: root.previewPageIndex = 3
        }

        Controls.MenuSeparator {}

        Controls.MenuItem {
            text: qsTr("About Linux Subsystem")
            onTriggered: {
                root.previewMessage = qsTr("About information is not part of this UI preview.")
                previewNotice.open()
            }
        }
    }

    StackLayout {
        anchors.fill: parent
        anchors.margins: 24
        currentIndex: root.previewPageIndex

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
                    id: welcomeHero

                    Layout.fillWidth: true
                    Layout.maximumWidth: 680
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 40

                    transform: Translate {
                        y: welcomeScroll.availableHeight > welcomeHero.implicitHeight + 48 ? -18 : 0
                    }

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
                            wrapMode: Text.Wrap
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            text: qsTr("Set up cubelinux Runtime for Linux apps and development tools. An internet connection is needed for the initial download.")
                            opacity: 0.8
                            wrapMode: Text.Wrap
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 16

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

                                Item {
                                    Layout.preferredWidth: 56
                                    Layout.preferredHeight: 56

                                    Image {
                                        anchors.centerIn: parent
                                        width: 56
                                        height: 56
                                        source: previewIconUrl
                                        sourceSize.width: 128
                                        sourceSize.height: 128
                                        fillMode: Image.PreserveAspectFit
                                    }
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

                                Item {
                                    Layout.preferredWidth: 56
                                    Layout.preferredHeight: 56

                                    Controls.Label {
                                        anchors.centerIn: parent
                                        text: "⌂"
                                        font.pixelSize: 34
                                        color: systemPalette.highlight
                                    }
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

        Controls.ScrollView {
            id: workspaceScroll

            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                id: workspaceContent

                width: Math.min(workspaceScroll.availableWidth, 760)
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 24

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Controls.Label {
                        text: qsTr("Linux environments")
                        font.pixelSize: 26
                        font.bold: true
                    }

                    Controls.Label {
                        text: qsTr("Your environment is ready to open.")
                        opacity: 0.75
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: runtimePreviewContent.implicitHeight + 32
                    radius: 8
                    color: systemPalette.base
                    border.color: systemPalette.mid

                    ColumnLayout {
                        id: runtimePreviewContent
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 16

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 16

                            Image {
                                source: previewIconUrl
                                sourceSize.width: 128
                                sourceSize.height: 128
                                fillMode: Image.PreserveAspectFit
                                Layout.preferredWidth: 64
                                Layout.preferredHeight: 64
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                RowLayout {
                                    spacing: 12

                                    Controls.Label {
                                        text: qsTr("cubelinux Runtime")
                                        font.pixelSize: 20
                                        font.bold: true
                                    }

                                    Controls.Label {
                                        text: qsTr("DEFAULT")
                                        font.pixelSize: 11
                                        font.bold: true
                                        opacity: 0.7
                                    }
                                }

                                Controls.Label {
                                    text: qsTr("cubelinux Runtime · x86_64")
                                    opacity: 0.75
                                }
                            }

                            RowLayout {
                                spacing: 8

                                Controls.Label {
                                    text: "●"
                                    color: systemPalette.highlight
                                }

                                Controls.Label {
                                    text: qsTr("Running")
                                    color: systemPalette.highlight
                                    font.bold: true
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: systemPalette.mid
                            opacity: 0.5
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 16

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
                                onClicked: previewController.openShell()
                            }
                        }
                    }
                }

                Controls.Button {
                    text: qsTr("Environment settings")
                    icon.name: "configure"
                    onClicked: root.previewPageIndex = 3
                }
            }
        }

        Controls.ScrollView {
            id: settingsScroll

            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                id: settingsContent

                width: Math.min(settingsScroll.availableWidth, 760)
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 24

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Controls.Label {
                        text: qsTr("Shared folders")
                        font.pixelSize: 24
                        font.bold: true
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Choose which cubelinux folders are available to cubelinux Runtime.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    Controls.Label {
                        text: "⌂"
                        font.pixelSize: 30
                        color: systemPalette.highlight
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Controls.Label {
                            text: qsTr("Home folder")
                            font.bold: true
                        }

                        Controls.Label {
                            text: qsTr("Shared automatically with cubelinux Runtime at %1.").arg(previewController.sharedHomePath)
                            opacity: 0.75
                            wrapMode: Text.Wrap
                        }
                    }

                    Controls.Label {
                        text: qsTr("Shared")
                        opacity: 0.75
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: systemPalette.mid
                    opacity: 0.5
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Controls.Label {
                                text: qsTr("Additional folders")
                                font.pixelSize: 20
                                font.bold: true
                            }

                            Controls.Label {
                                text: qsTr("Manage folders shared with cubelinux Runtime.")
                                opacity: 0.75
                                wrapMode: Text.Wrap
                            }
                        }

                        Controls.Button {
                            text: qsTr("Add folder…")
                            icon.name: "folder-open"
                            onClicked: previewController.chooseSharedFolder()
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16

                        Controls.Label {
                            text: "▱"
                            font.pixelSize: 26
                            color: systemPalette.highlight
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Controls.Label {
                                text: qsTr("Projects")
                                font.bold: true
                            }

                            Controls.Label {
                                text: qsTr("~/Projects → /mnt/vshell-shares/projects")
                                opacity: 0.75
                            }
                        }

                        Controls.ToolButton {
                            icon.name: "edit-delete"
                            Accessible.name: qsTr("Remove shared folder")
                            onClicked: previewController.removeSharedFolder("preview-projects")
                        }
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Runtime can read and modify shared folders. Changing folder access restarts the Runtime when it is running.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: systemPalette.mid
                    opacity: 0.5
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Controls.Label {
                        text: qsTr("Port forwarding")
                        font.pixelSize: 20
                        font.bold: true
                    }

                    Controls.Label {
                        Layout.fillWidth: true
                        text: qsTr("Runtime TCP services on ports 1024 and above are forwarded to this host automatically.")
                        opacity: 0.75
                        wrapMode: Text.Wrap
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Controls.Label {
                                text: qsTr("TCP port 3000 in cubelinux Runtime")
                                font.bold: true
                            }

                            Controls.Label {
                                text: qsTr("Available on this host at 127.0.0.1:3000")
                                opacity: 0.75
                            }
                        }

                        ColumnLayout {
                            Controls.Label {
                                text: qsTr("Expose to public")
                                font.bold: true
                            }

                            Controls.Switch {
                                checked: false
                                Accessible.name: qsTr("Expose port 3000 to public networks")
                                onToggled: previewController.setPortPublicAccess(3000, checked)
                            }
                        }
                    }
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
            text: root.previewMessage
            wrapMode: Text.Wrap
        }
    }
}
