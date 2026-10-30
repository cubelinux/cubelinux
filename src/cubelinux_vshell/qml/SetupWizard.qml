import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: wizard

    property var controller
    property bool darkTheme: false
    property int wizardStep: 0
    readonly property var setupStages: [
        qsTr("Preparing your account"),
        qsTr("Downloading Fedora"),
        qsTr("Creating your environment"),
        qsTr("Connecting Linux to your desktop")
    ]
    readonly property int activeSetupStage: {
        const title = controller.progressTitle.toLowerCase()
        if (title === "setup complete") return setupStages.length
        if (title.indexOf("preparing your account") >= 0
                || title.indexOf("container networking") >= 0) return 0
        if (title.indexOf("download") >= 0
                || title.indexOf("checking for fedora") >= 0
                || title.indexOf("checking the fedora image") >= 0
                || title.indexOf("extracting fedora") >= 0
                || title.indexOf("cached fedora image") >= 0) return 1
        if (title.indexOf("desktop session") >= 0
                || title.indexOf("restarting fedora") >= 0) return 3
        return 2
    }

    function startOver() {
        wizardStep = 0
    }

    function showFailure() {
        wizardStep = 2
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.fillHeight: true
            visible: wizard.wizardStep < 2
        }

        Kirigami.Card {
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            Layout.fillHeight: wizard.wizardStep === 2
            Layout.maximumWidth: 620
            Layout.preferredHeight: 500

            contentItem: ColumnLayout {
                spacing: Kirigami.Units.mediumSpacing

                RowLayout {
                    Layout.fillWidth: true

                    Controls.Label {
                        text: qsTr("STEP %1 OF 3").arg(wizard.wizardStep + 1)
                        font.bold: true
                        opacity: 0.7
                    }

                    Item { Layout.fillWidth: true }

                    Controls.Label {
                        text: qsTr("Fedora Linux 44")
                        opacity: 0.7
                    }
                }

                Controls.ProgressBar {
                    Layout.fillWidth: true
                    from: 0
                    to: 3
                    value: wizard.wizardStep + 1
                }

                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: wizard.wizardStep

                    ColumnLayout {
                        spacing: Kirigami.Units.mediumSpacing

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.largeSpacing

                            Image {
                                source: wizard.darkTheme
                                        ? "file:///usr/share/fedora-logos/fedora_logo_darkbackground.svg"
                                        : "file:///usr/share/fedora-logos/fedora_logo.svg"
                                sourceSize.width: 144
                                sourceSize.height: 72
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                Layout.preferredWidth: 88
                                Layout.preferredHeight: Kirigami.Units.iconSizes.large
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.smallSpacing

                                Kirigami.Heading {
                                    text: qsTr("Set up Linux")
                                    level: 2
                                }

                                Controls.Label {
                                    Layout.fillWidth: true
                                    text: qsTr("A Linux environment for your apps and development tools.")
                                    opacity: 0.7
                                    wrapMode: Text.Wrap
                                }
                            }
                        }

                        Kirigami.Card {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 80

                            contentItem: RowLayout {
                                spacing: Kirigami.Units.mediumSpacing

                                Image {
                                    source: wizard.darkTheme
                                            ? "file:///usr/share/fedora-logos/fedora_logo_darkbackground.svg"
                                            : "file:///usr/share/fedora-logos/fedora_logo.svg"
                                    sourceSize.width: 96
                                    sourceSize.height: 48
                                    fillMode: Image.PreserveAspectFit
                                    Layout.preferredWidth: 56
                                    Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0

                                    Controls.Label {
                                        text: qsTr("Fedora Linux 44")
                                        font.bold: true
                                    }

                                    Controls.Label {
                                        text: qsTr("Default environment")
                                        opacity: 0.7
                                    }
                                }

                                Kirigami.Icon {
                                    source: "emblem-checked"
                                    color: Kirigami.Theme.positiveTextColor
                                    Layout.preferredWidth: Kirigami.Units.iconSizes.small
                                    Layout.preferredHeight: Kirigami.Units.iconSizes.small
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Controls.Label {
                                text: qsTr("What you get")
                                font.bold: true
                            }

                            Controls.Label {
                                Layout.fillWidth: true
                                text: qsTr("Linux apps alongside your cubelinux apps")
                                opacity: 0.75
                                wrapMode: Text.Wrap
                            }

                            Controls.Label {
                                Layout.fillWidth: true
                                text: qsTr("A Fedora terminal for command-line tools")
                                opacity: 0.75
                                wrapMode: Text.Wrap
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }

                    ColumnLayout {
                        spacing: Kirigami.Units.mediumSpacing

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Kirigami.Heading {
                                text: qsTr("Before you begin")
                                level: 2
                            }

                            Controls.Label {
                                Layout.fillWidth: true
                                text: qsTr("Fedora will be set up as your Linux environment.")
                                opacity: 0.7
                                wrapMode: Text.Wrap
                            }
                        }

                        Kirigami.Card {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 76

                            contentItem: RowLayout {
                                spacing: Kirigami.Units.mediumSpacing

                                Image {
                                    source: wizard.darkTheme
                                            ? "file:///usr/share/fedora-logos/fedora_logo_darkbackground.svg"
                                            : "file:///usr/share/fedora-logos/fedora_logo.svg"
                                    sourceSize.width: 96
                                    sourceSize.height: 48
                                    fillMode: Image.PreserveAspectFit
                                    Layout.preferredWidth: 56
                                    Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0

                                    Controls.Label {
                                        text: qsTr("Fedora Linux 44")
                                        font.bold: true
                                    }

                                    Controls.Label {
                                        text: qsTr("Installed apps and data stay in Fedora.")
                                        opacity: 0.7
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }

                        Kirigami.Card {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 96

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
                                        Layout.fillWidth: true
                                        text: qsTr("Your files are available at %1 in Fedora.").arg(controller.sharedHomePath)
                                        opacity: 0.7
                                        wrapMode: Text.Wrap
                                    }

                                    Controls.Label {
                                        Layout.fillWidth: true
                                        text: qsTr("Other folders can be added later in settings.")
                                        opacity: 0.7
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            text: qsTr("Your shared home files stay on cubelinux if you destroy Fedora.")
                            opacity: 0.7
                            wrapMode: Text.Wrap
                        }

                        Item { Layout.fillHeight: true }
                    }

                    ColumnLayout {
                        spacing: Kirigami.Units.mediumSpacing

                        Item { Layout.fillHeight: true }

                        Controls.BusyIndicator {
                            Layout.alignment: Qt.AlignHCenter
                            running: controller.busy
                            visible: running
                            implicitWidth: Kirigami.Units.iconSizes.large
                            implicitHeight: Kirigami.Units.iconSizes.large
                        }

                        Kirigami.Heading {
                            Layout.alignment: Qt.AlignHCenter
                            text: controller.busy
                                  ? qsTr("Setting up Linux")
                                  : qsTr("Setup needs attention")
                            level: 2
                        }

                        Controls.Label {
                            Layout.alignment: Qt.AlignHCenter
                            visible: controller.busy
                            text: qsTr("This can take a few minutes.")
                            opacity: 0.7
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            visible: controller.busy && controller.progress.length > 0
                            text: controller.progress
                            opacity: 0.7
                            wrapMode: Text.Wrap
                        }

                        Controls.ProgressBar {
                            Layout.fillWidth: true
                            visible: controller.busy
                            from: 0
                            to: 100
                            value: Math.max(0, controller.progressPercent)
                            indeterminate: controller.progressPercent < 0
                        }

                        Repeater {
                            model: wizard.setupStages

                            delegate: RowLayout {
                                required property int index
                                required property string modelData

                                Layout.fillWidth: true
                                spacing: Kirigami.Units.mediumSpacing

                                Kirigami.Icon {
                                    source: index < wizard.activeSetupStage
                                            ? "emblem-checked"
                                            : index === wizard.activeSetupStage
                                              ? "media-playback-start" : "media-playback-stop"
                                    color: index < wizard.activeSetupStage
                                           ? Kirigami.Theme.positiveTextColor
                                           : index === wizard.activeSetupStage
                                             ? Kirigami.Theme.textColor
                                             : Kirigami.Theme.neutralTextColor
                                    implicitWidth: Kirigami.Units.iconSizes.small
                                    implicitHeight: Kirigami.Units.iconSizes.small
                                    Accessible.name: modelData
                                }

                                Controls.Label {
                                    Layout.fillWidth: true
                                    text: modelData
                                    font.bold: index === wizard.activeSetupStage
                                    opacity: index > wizard.activeSetupStage ? 0.55 : 1.0
                                }
                            }
                        }

                        Kirigami.Card {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 68
                            visible: controller.busy

                            contentItem: RowLayout {
                                spacing: Kirigami.Units.mediumSpacing

                                Kirigami.Icon {
                                    source: "dialog-information"
                                    implicitWidth: Kirigami.Units.iconSizes.small
                                    implicitHeight: Kirigami.Units.iconSizes.small
                                }

                                Controls.Label {
                                    Layout.fillWidth: true
                                    text: qsTr("You can close this window. Setup will continue, and you can reopen it to check.")
                                    opacity: 0.75
                                    wrapMode: Text.Wrap
                                }
                            }
                        }

                        Kirigami.InlineMessage {
                            Layout.fillWidth: true
                            visible: !controller.busy && controller.progress.length > 0
                            text: controller.progress
                            type: controller.progressTitle === qsTr("Setup failed")
                                  || controller.progressTitle === qsTr("Destroy failed")
                                  ? Kirigami.MessageType.Error : Kirigami.MessageType.Information
                        }

                        Item { Layout.fillHeight: true }
                    }
                }

                Kirigami.Separator {
                    Layout.fillWidth: true
                    visible: wizard.wizardStep < 2 || !controller.busy
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: wizard.wizardStep < 2 || !controller.busy

                    Controls.Button {
                        visible: wizard.wizardStep === 0
                        text: qsTr("Cancel")
                        onClicked: Qt.quit()
                    }

                    Controls.Button {
                        visible: wizard.wizardStep === 1
                        text: qsTr("Back")
                        onClicked: wizard.wizardStep = 0
                    }

                    Item { Layout.fillWidth: true }

                    Controls.Button {
                        visible: wizard.wizardStep === 0
                        text: qsTr("Next")
                        highlighted: true
                        onClicked: wizard.wizardStep = 1
                    }

                    Controls.Button {
                        visible: wizard.wizardStep === 1
                        text: qsTr("Set up Linux")
                        highlighted: true
                        enabled: !controller.busy
                        onClicked: {
                            wizard.wizardStep = 2
                            controller.setup()
                        }
                    }

                    Controls.Button {
                        visible: wizard.wizardStep === 2 && !controller.busy
                        text: controller.progressTitle === qsTr("Destroy failed")
                              ? qsTr("Retry destruction") : qsTr("Try again")
                        highlighted: true
                        onClicked: controller.progressTitle === qsTr("Destroy failed")
                                   ? controller.destroyContainer() : controller.setup()
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
            visible: wizard.wizardStep < 2
        }
    }
}
