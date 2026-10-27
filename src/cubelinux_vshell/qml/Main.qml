import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("Setup Terminal")
    width: 920
    height: 700
    minimumWidth: 760
    minimumHeight: 600
    visible: true

    readonly property color brandBlue: "#2d9bd2"
    property int wizardStep: 0

    pageStack.initialPage: Kirigami.Page {
        title: qsTr("Setup Terminal")
        padding: Kirigami.Units.largeSpacing

        ColumnLayout {
            anchors.fill: parent
            spacing: Kirigami.Units.largeSpacing

            StackLayout {
                id: screens
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: setupController.ready ? 1 : 0

                // First-run setup flow
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: Kirigami.Units.largeSpacing

                        RowLayout {
                            Layout.fillWidth: true

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.smallSpacing

                                Kirigami.Heading {
                                    text: qsTr("Setup Terminal")
                                    level: 1
                                }

                                Controls.Label {
                                    text: qsTr("A Fedora workspace for your tools and development work.")
                                    opacity: 0.75
                                    wrapMode: Text.Wrap
                                }
                            }

                            Controls.Label {
                                text: qsTr("STEP %1 OF 3").arg(wizardStep + 1)
                                font.bold: true
                                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                                opacity: 0.65
                            }
                        }

                        Controls.ProgressBar {
                            Layout.fillWidth: true
                            from: 0
                            to: 3
                            value: wizardStep + 1
                            background: Rectangle {
                                implicitHeight: 4
                                radius: 2
                                color: Kirigami.Theme.alternateBackgroundColor
                            }
                            contentItem: Item {
                                Rectangle {
                                    width: parent.width * (wizardStep + 1) / 3
                                    height: parent.height
                                    radius: 2
                                    color: root.brandBlue
                                }
                            }
                        }

                        StackLayout {
                            id: setupSteps
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            currentIndex: wizardStep

                            // Step 1: choose the supplied Linux environment
                            ColumnLayout {
                                Layout.alignment: Qt.AlignTop
                                spacing: Kirigami.Units.largeSpacing

                                Controls.Label {
                                    text: qsTr("LINUX ENVIRONMENT")
                                    font.bold: true
                                    font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                                    opacity: 0.65
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 112
                                    radius: 17
                                    color: Kirigami.Theme.backgroundColor
                                    border.color: Kirigami.Theme.alternateBackgroundColor

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: Kirigami.Units.largeSpacing
                                        spacing: Kirigami.Units.largeSpacing

                                        Rectangle {
                                            Layout.preferredWidth: 72
                                            Layout.preferredHeight: 72
                                            radius: 20
                                            color: "#eaf5fa"

                                            Kirigami.Icon {
                                                anchors.centerIn: parent
                                                source: "utilities-terminal"
                                                width: 38
                                                height: 38
                                                color: root.brandBlue
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: Kirigami.Units.smallSpacing

                                            Kirigami.Heading {
                                                text: qsTr("Fedora Linux")
                                                level: 3
                                            }

                                            Controls.Label {
                                                text: qsTr("Fedora 44 · Default environment")
                                                opacity: 0.7
                                            }
                                        }

                                        Kirigami.Icon {
                                            source: "go-next"
                                            width: Kirigami.Units.iconSizes.small
                                            height: width
                                            opacity: 0.55
                                        }
                                    }
                                }

                                Controls.Label {
                                    Layout.fillWidth: true
                                    text: qsTr("A separate Linux environment that works alongside cubelinux.")
                                    opacity: 0.75
                                    wrapMode: Text.Wrap
                                }

                                Item { Layout.fillHeight: true }
                            }

                            // Step 2: confirm sharing and the default environment name
                            ColumnLayout {
                                Layout.alignment: Qt.AlignTop
                                spacing: Kirigami.Units.largeSpacing

                                Kirigami.Heading {
                                    text: qsTr("Ready to set up")
                                    level: 2
                                }

                                Controls.Label {
                                    text: qsTr("Your environment will be called cubelinux.")
                                    opacity: 0.75
                                    wrapMode: Text.Wrap
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 76
                                    radius: 16
                                    color: Kirigami.Theme.alternateBackgroundColor

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: Kirigami.Units.mediumSpacing
                                        spacing: Kirigami.Units.mediumSpacing

                                        Kirigami.Icon {
                                            source: "folder-home"
                                            width: Kirigami.Units.iconSizes.medium
                                            height: width
                                            color: root.brandBlue
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: Kirigami.Units.smallSpacing

                                            Controls.Label {
                                                text: qsTr("Home folder shared")
                                                font.bold: true
                                            }

                                            Controls.Label {
                                                text: qsTr("Your files are available in both systems.")
                                                opacity: 0.7
                                                wrapMode: Text.Wrap
                                            }
                                        }
                                    }
                                }

                                Item { Layout.fillHeight: true }
                            }

                            // Step 3: show setup progress and recoverable errors
                            ColumnLayout {
                                Layout.alignment: Qt.AlignTop
                                spacing: Kirigami.Units.largeSpacing

                                Kirigami.Heading {
                                    Layout.fillWidth: true
                                    text: setupController.busy
                                          ? setupController.progressTitle
                                          : (setupController.progressTitle === qsTr("Setup failed")
                                             ? qsTr("Setup needs attention")
                                             : qsTr("Ready to set up"))
                                    level: 2
                                    wrapMode: Text.Wrap
                                }

                                Controls.Label {
                                    Layout.fillWidth: true
                                    visible: setupController.busy || setupController.progress.length > 0
                                    text: setupController.progress
                                    color: setupController.progressTitle === qsTr("Setup failed")
                                           ? Kirigami.Theme.negativeTextColor
                                           : Kirigami.Theme.textColor
                                    opacity: 0.8
                                    wrapMode: Text.Wrap
                                }

                                Controls.ProgressBar {
                                    Layout.fillWidth: true
                                    visible: setupController.busy
                                    from: 0
                                    to: 100
                                    value: Math.max(0, setupController.progressPercent)
                                    indeterminate: setupController.progressPercent < 0
                                }

                                Item { Layout.fillHeight: true }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true

                            Controls.Label {
                                text: qsTr("cubelinux · %1").arg(softwareVersion)
                                opacity: 0.55
                                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                            }

                            Item { Layout.fillWidth: true }

                            Controls.Button {
                                text: qsTr("Back")
                                visible: wizardStep > 0 && wizardStep < 2 && !setupController.busy
                                onClicked: wizardStep -= 1
                            }

                            Controls.Button {
                                id: nextButton
                                visible: wizardStep < 2
                                text: qsTr("Next")
                                highlighted: true
                                onClicked: wizardStep += 1
                                background: Rectangle {
                                    radius: 12
                                    color: root.brandBlue
                                }
                                contentItem: Controls.Label {
                                    text: nextButton.text
                                    color: "white"
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }

                            Controls.Button {
                                id: setupButton
                                visible: wizardStep === 2
                                enabled: !setupController.busy
                                highlighted: true
                                text: setupController.progressTitle === qsTr("Setup failed")
                                      ? qsTr("Try again") : qsTr("Set up")
                                onClicked: setupController.setup()
                                background: Rectangle {
                                    radius: 12
                                    color: root.brandBlue
                                }
                                contentItem: Controls.Label {
                                    text: setupButton.text
                                    color: "white"
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }
                    }
                }

                // Manager home after setup
                RowLayout {
                    spacing: Kirigami.Units.largeSpacing

                    Rectangle {
                        Layout.preferredWidth: 190
                        Layout.fillHeight: true
                        radius: 16
                        color: Kirigami.Theme.alternateBackgroundColor

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: Kirigami.Units.mediumSpacing
                            spacing: Kirigami.Units.largeSpacing

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.mediumSpacing

                                Rectangle {
                                    Layout.preferredWidth: 34
                                    Layout.preferredHeight: 34
                                    radius: 11
                                    color: root.brandBlue

                                    Kirigami.Icon {
                                        anchors.centerIn: parent
                                        source: "utilities-terminal"
                                        width: 19
                                        height: 19
                                        color: "white"
                                    }
                                }

                                ColumnLayout {
                                    spacing: 0
                                    Controls.Label {
                                        text: qsTr("Setup Terminal")
                                        font.bold: true
                                    }
                                    Controls.Label {
                                        text: qsTr("cubelinux")
                                        font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 2
                                        opacity: 0.65
                                    }
                                }
                            }

                            Controls.Button {
                                id: overviewButton
                                Layout.fillWidth: true
                                text: qsTr("Overview")
                                highlighted: true
                                background: Rectangle {
                                    radius: 12
                                    color: "#e7f4fa"
                                }
                                contentItem: Controls.Label {
                                    text: overviewButton.text
                                    color: "#237da8"
                                    font.bold: true
                                    horizontalAlignment: Text.AlignLeft
                                    verticalAlignment: Text.AlignVCenter
                                    leftPadding: Kirigami.Units.mediumSpacing
                                }
                            }

                            Item { Layout.fillHeight: true }

                            RowLayout {
                                spacing: Kirigami.Units.smallSpacing
                                Rectangle {
                                    Layout.preferredWidth: 9
                                    Layout.preferredHeight: 9
                                    radius: 5
                                    color: setupController.containerStatus === "running" ? "#2aa77a" : root.brandBlue
                                }
                                Controls.Label {
                                    text: setupController.containerStatus === "running"
                                          ? qsTr("Fedora is running") : qsTr("Fedora is ready")
                                    font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 2
                                    opacity: 0.8
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Kirigami.Units.largeSpacing

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Controls.Label {
                                text: qsTr("YOUR WORKSPACE")
                                font.bold: true
                                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                                opacity: 0.65
                            }

                            Kirigami.Heading {
                                text: qsTr("Your workspace")
                                level: 1
                            }

                            Controls.Label {
                                text: qsTr("Your Linux tools, in one place.")
                                opacity: 0.7
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 290
                            radius: 19
                            color: Kirigami.Theme.backgroundColor
                            border.color: Kirigami.Theme.alternateBackgroundColor

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: Kirigami.Units.largeSpacing
                                spacing: Kirigami.Units.mediumSpacing

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.largeSpacing

                                    Rectangle {
                                        Layout.preferredWidth: 72
                                        Layout.preferredHeight: 72
                                        radius: 21
                                        color: "#eaf5fa"
                                        Kirigami.Icon {
                                            anchors.centerIn: parent
                                            source: "utilities-terminal"
                                            width: 38
                                            height: 38
                                            color: root.brandBlue
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: Kirigami.Units.smallSpacing

                                        Kirigami.Heading {
                                            text: qsTr("cubelinux")
                                            level: 2
                                        }
                                        Controls.Label {
                                            text: qsTr("Fedora 44 · Default environment")
                                            opacity: 0.7
                                        }
                                    }

                                    Rectangle {
                                        Layout.preferredWidth: statusLabel.implicitWidth + 24
                                        Layout.preferredHeight: 28
                                        radius: 14
                                        color: setupController.containerStatus === "running" ? "#e8f6f1" : "#eaf5fa"
                                        RowLayout {
                                            anchors.centerIn: parent
                                            spacing: 7
                                            Rectangle {
                                                Layout.preferredWidth: 7
                                                Layout.preferredHeight: 7
                                                radius: 4
                                                color: setupController.containerStatus === "running" ? "#2aa77a" : root.brandBlue
                                            }
                                            Controls.Label {
                                                id: statusLabel
                                                text: setupController.containerStatus === "running"
                                                      ? qsTr("RUNNING") : qsTr("STOPPED")
                                                font.bold: true
                                                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 2
                                                color: setupController.containerStatus === "running" ? "#267d61" : "#237da8"
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 1
                                    color: Kirigami.Theme.alternateBackgroundColor
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.mediumSpacing

                                    Kirigami.Icon {
                                        source: "folder-home"
                                        width: Kirigami.Units.iconSizes.small
                                        height: width
                                        color: root.brandBlue
                                    }

                                    ColumnLayout {
                                        spacing: 0
                                        Controls.Label {
                                            text: qsTr("Home folder shared")
                                            font.bold: true
                                        }
                                        Controls.Label {
                                            text: qsTr("Your files are available inside Fedora.")
                                            opacity: 0.7
                                        }
                                    }
                                    Item { Layout.fillWidth: true }
                                }

                                Item { Layout.fillHeight: true }

                                Controls.Button {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 48
                                    text: qsTr("Open terminal")
                                    highlighted: true
                                    onClicked: setupController.openShell()
                                    background: Rectangle {
                                        radius: 13
                                        color: root.brandBlue
                                    }
                                    contentItem: RowLayout {
                                        spacing: Kirigami.Units.mediumSpacing
                                        Item { Layout.fillWidth: true }
                                        Kirigami.Icon {
                                            source: "utilities-terminal"
                                            width: Kirigami.Units.iconSizes.small
                                            height: width
                                            color: "white"
                                        }
                                        Controls.Label {
                                            text: qsTr("Open terminal")
                                            font.bold: true
                                            color: "white"
                                        }
                                        Item { Layout.fillWidth: true }
                                    }
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }

                        Controls.Label {
                            text: qsTr("cubelinux · Setup Terminal %1").arg(softwareVersion)
                            font.pixelSize: Kirigami.Theme.defaultFont.pixelSize - 1
                            opacity: 0.55
                        }
                    }
                }
            }
        }

        Timer {
            interval: 2500
            repeat: true
            running: setupController.ready
            onTriggered: setupController.refreshStatus()
        }

        Component.onCompleted: setupController.refreshStatus()
    }
}
