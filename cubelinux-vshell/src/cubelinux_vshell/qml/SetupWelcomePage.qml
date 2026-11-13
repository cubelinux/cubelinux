import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Controls.ScrollView {
    id: page

    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        id: content

        width: page.availableWidth
        height: Math.max(page.availableHeight, content.implicitHeight)
        spacing: 0

        Item {
            Layout.fillHeight: true
            Layout.minimumHeight: Kirigami.Units.largeSpacing
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 42
            Layout.alignment: Qt.AlignHCenter
            spacing: Kirigami.Units.largeSpacing * 1.5

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.mediumSpacing

                Image {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 88
                    Layout.preferredHeight: 88
                    source: "cubelinux-icon.svg"
                    sourceSize.width: 128
                    sourceSize.height: 128
                    fillMode: Image.PreserveAspectFit
                    Accessible.name: qsTr("cubelinux")
                }

                Kirigami.Heading {
                    Layout.fillWidth: true
                    text: qsTr("Linux apps, at home on cubelinux")
                    level: 1
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                }

                Controls.Label {
                    Layout.fillWidth: true
                    text: qsTr("Create a Fedora workspace for Linux apps and development tools, alongside your cubelinux desktop.")
                    opacity: 0.8
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.mediumSpacing

                Kirigami.Heading {
                    Layout.fillWidth: true
                    text: qsTr("What you get")
                    level: 2
                }

                Kirigami.CardsLayout {
                    Layout.fillWidth: true
                    maximumColumns: 2

                    Kirigami.AbstractCard {
                        Layout.fillWidth: true

                        contentItem: RowLayout {
                            spacing: Kirigami.Units.mediumSpacing

                            Kirigami.Icon {
                                source: "applications-all"
                                implicitWidth: Kirigami.Units.iconSizes.large
                                implicitHeight: Kirigami.Units.iconSizes.large
                                color: Kirigami.Theme.highlightColor
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.smallSpacing

                                Kirigami.Heading {
                                    Layout.fillWidth: true
                                    text: qsTr("Linux apps")
                                    level: 3
                                }

                                Controls.Label {
                                    Layout.fillWidth: true
                                    text: qsTr("Run graphical Linux apps alongside your cubelinux apps.")
                                    opacity: 0.75
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }

                    Kirigami.AbstractCard {
                        Layout.fillWidth: true

                        contentItem: RowLayout {
                            spacing: Kirigami.Units.mediumSpacing

                            Kirigami.Icon {
                                source: "utilities-terminal"
                                implicitWidth: Kirigami.Units.iconSizes.large
                                implicitHeight: Kirigami.Units.iconSizes.large
                                color: Kirigami.Theme.highlightColor
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.smallSpacing

                                Kirigami.Heading {
                                    Layout.fillWidth: true
                                    text: qsTr("Fedora tools")
                                    level: 3
                                }

                                Controls.Label {
                                    Layout.fillWidth: true
                                    text: qsTr("Use a Fedora terminal for command-line tools and development.")
                                    opacity: 0.75
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
            Layout.minimumHeight: Kirigami.Units.largeSpacing
        }
    }
}
