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

    property int wizardStep: 0

    pageStack.initialPage: Kirigami.Page {
        title: qsTr("Setup Terminal")
        padding: Kirigami.Units.largeSpacing

        ColumnLayout {
            anchors.fill: parent
            spacing: Kirigami.Units.largeSpacing

            StackLayout {
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
                                opacity: 0.7
                            }
                        }

                        Controls.ProgressBar {
                            Layout.fillWidth: true
                            from: 0
                            to: 3
                            value: wizardStep + 1
                        }

                        StackLayout {
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
                                    opacity: 0.7
                                }

                                Kirigami.Card {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 112

                                    contentItem: RowLayout {
                                        spacing: Kirigami.Units.largeSpacing

                                        Kirigami.Icon {
                                            source: "utilities-terminal"
                                            Layout.preferredWidth: Kirigami.Units.iconSizes.large
                                            Layout.preferredHeight: Kirigami.Units.iconSizes.large
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
                                            Layout.preferredWidth: Kirigami.Units.iconSizes.small
                                            Layout.preferredHeight: Kirigami.Units.iconSizes.small
                                            opacity: 0.65
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

                                Kirigami.Card {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 76

                                    contentItem: RowLayout {
                                        spacing: Kirigami.Units.mediumSpacing

                                        Kirigami.Icon {
                                            source: "folder-home"
                                            Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                                            Layout.preferredHeight: Kirigami.Units.iconSizes.medium
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

                                Kirigami.InlineMessage {
                                    Layout.fillWidth: true
                                    visible: setupController.busy || setupController.progress.length > 0
                                    text: setupController.progress
                                    type: setupController.progressTitle === qsTr("Setup failed")
                                          ? Kirigami.MessageType.Error
                                          : Kirigami.MessageType.Information
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
                                visible: wizardStep < 2
                                text: qsTr("Next")
                                highlighted: true
                                onClicked: wizardStep += 1
                            }

                            Controls.Button {
                                visible: wizardStep === 2
                                enabled: !setupController.busy
                                highlighted: true
                                text: setupController.progressTitle === qsTr("Setup failed")
                                      ? qsTr("Try again") : qsTr("Set up")
                                onClicked: setupController.setup()
                            }
                        }
                    }
                }

                // Manager home after setup, preserving the current left navigation
                // and workspace card placement.
                RowLayout {
                    spacing: Kirigami.Units.largeSpacing

                    Kirigami.Card {
                        Layout.preferredWidth: 190
                        Layout.fillHeight: true

                        contentItem: ColumnLayout {
                            spacing: Kirigami.Units.largeSpacing

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.mediumSpacing

                                Kirigami.Icon {
                                    source: "utilities-terminal"
                                    Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                                    Layout.preferredHeight: Kirigami.Units.iconSizes.medium
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
                                Layout.fillWidth: true
                                text: qsTr("Overview")
                                icon.name: "view-dashboard"
                                highlighted: true
                            }

                            Item { Layout.fillHeight: true }

                            RowLayout {
                                spacing: Kirigami.Units.smallSpacing

                                Kirigami.Icon {
                                    source: setupController.containerStatus === "running"
                                            ? "emblem-success" : "media-playback-stop"
                                    Layout.preferredWidth: Kirigami.Units.iconSizes.small
                                    Layout.preferredHeight: Kirigami.Units.iconSizes.small
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

                        Kirigami.Card {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 290

                            contentItem: ColumnLayout {
                                spacing: Kirigami.Units.mediumSpacing

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.largeSpacing

                                    Kirigami.Icon {
                                        source: "utilities-terminal"
                                        Layout.preferredWidth: Kirigami.Units.iconSizes.large
                                        Layout.preferredHeight: Kirigami.Units.iconSizes.large
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

                                    Controls.Label {
                                        text: setupController.containerStatus === "running"
                                              ? qsTr("Running") : qsTr("Stopped")
                                        font.bold: true
                                    }
                                }

                                Kirigami.Separator {
                                    Layout.fillWidth: true
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Kirigami.Units.mediumSpacing

                                    Kirigami.Icon {
                                        source: "folder-home"
                                        Layout.preferredWidth: Kirigami.Units.iconSizes.small
                                        Layout.preferredHeight: Kirigami.Units.iconSizes.small
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
                                    icon.name: "utilities-terminal"
                                    highlighted: true
                                    onClicked: setupController.openShell()
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
