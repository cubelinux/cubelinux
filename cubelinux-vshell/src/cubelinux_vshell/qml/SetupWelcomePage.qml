import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Controls.ScrollView {
    id: page

    property url logoSource: "cubelinux-icon.png"

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
            id: heroContent

            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 42
            Layout.alignment: Qt.AlignHCenter
            spacing: Kirigami.Units.largeSpacing * 1.5

            transform: Translate {
                y: page.availableHeight > heroContent.implicitHeight + Kirigami.Units.largeSpacing * 2
                   ? -Kirigami.Units.gridUnit : 0
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.mediumSpacing

                Image {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 88
                    Layout.preferredHeight: 88
                    source: page.logoSource
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
                    text: qsTr("Set up cubelinux Runtime to run Linux apps and development tools alongside your desktop.")
                    opacity: 0.8
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.mediumSpacing

                Kirigami.Separator {
                    Layout.fillWidth: true
                }

                Kirigami.Heading {
                    Layout.fillWidth: true
                    text: qsTr("What you get")
                    level: 2
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: page.availableWidth >= 680 ? 2 : 1
                    columnSpacing: Kirigami.Units.largeSpacing
                    rowSpacing: Kirigami.Units.largeSpacing

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
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

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
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
                                text: qsTr("Development tools")
                                level: 3
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
            Layout.minimumHeight: Kirigami.Units.largeSpacing
        }
    }
}
