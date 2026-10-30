import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    property var controller
    property bool darkTheme: false
    property int wizardStep: 0

    function startOver() {
        wizardStep = 0
    }

    function showFailure() {
        wizardStep = 2
    }


                    ColumnLayout {
                        anchors.fill: parent
                        spacing: Kirigami.Units.largeSpacing

                        RowLayout {
                            Layout.fillWidth: true

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.smallSpacing

                                Kirigami.Heading {
                                    text: qsTr("Linux Subsystem")
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

                                        Image {
                                            source: darkTheme
                                                    ? "file:///usr/share/fedora-logos/fedora_logo_darkbackground.svg"
                                                    : "file:///usr/share/fedora-logos/fedora_logo.svg"
                                            sourceSize.width: 192
                                            sourceSize.height: 96
                                            fillMode: Image.PreserveAspectFit
                                            smooth: true
                                            Layout.preferredWidth: 96
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
                                    text: controller.busy
                                          ? controller.progressTitle
                                          : (controller.progressTitle === qsTr("Setup failed")
                                             || controller.progressTitle === qsTr("Destroy failed")
                                             ? (controller.progressTitle === qsTr("Destroy failed")
                                                ? qsTr("Destruction needs attention")
                                                : qsTr("Setup needs attention"))
                                             : qsTr("Ready to set up"))
                                    level: 2
                                    wrapMode: Text.Wrap
                                }

                                Kirigami.InlineMessage {
                                    Layout.fillWidth: true
                                    visible: controller.busy || controller.progress.length > 0
                                    text: controller.progress
                                    type: controller.progressTitle === qsTr("Setup failed")
                                          || controller.progressTitle === qsTr("Destroy failed")
                                          ? Kirigami.MessageType.Error
                                          : Kirigami.MessageType.Information
                                }

                                Controls.ProgressBar {
                                    Layout.fillWidth: true
                                    visible: controller.busy
                                    from: 0
                                    to: 100
                                    value: Math.max(0, controller.progressPercent)
                                    indeterminate: controller.progressPercent < 0
                                }

                                Item { Layout.fillHeight: true }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true

                            Item { Layout.fillWidth: true }

                            Controls.Button {
                                text: qsTr("Back")
                                visible: wizardStep > 0 && wizardStep < 2 && !controller.busy
                                onClicked: wizardStep -= 1
                            }

                            Controls.Button {
                                visible: wizardStep < 2
                                enabled: !controller.busy
                                text: qsTr("Next")
                                highlighted: true
                                onClicked: wizardStep += 1
                            }

                            Controls.Button {
                                visible: wizardStep === 2 && !controller.busy
                                highlighted: true
                                text: controller.progressTitle === qsTr("Destroy failed")
                                      ? qsTr("Retry destruction")
                                      : controller.progressTitle === qsTr("Setup failed")
                                        ? qsTr("Try again") : qsTr("Set up")
                                onClicked: controller.progressTitle === qsTr("Destroy failed")
                                           ? controller.destroyContainer()
                                           : controller.setup()
                            }
                        }
                    }
}
