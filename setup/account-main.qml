/* cubelinux account page for Plasma Setup.
 * AccountController remains responsible for validation and the KAuth helper
 * remains responsible for creating the account.
 */
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasmasetup
import org.kde.plasmasetup.components as PlasmaSetupComponents

PlasmaSetupComponents.SetupModule {
    id: root

    available: !AccountController.hasExistingUsers

    property bool usernameValid: AccountController.isUsernameValid(usernameField.text)
    property string usernameMessage: AccountController.usernameValidationMessage(usernameField.text)

    nextEnabled: usernameValid && passwordField.text.length > 0

    function onPageActivated() {
        usernameField.forceActiveFocus()
    }

    contentItem: ScrollView {
        clip: true

        ColumnLayout {
            width: Math.min(parent.width - Kirigami.Units.largeSpacing * 2, 680)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Kirigami.Units.largeSpacing

            Item { Layout.fillHeight: true }

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Image {
                    source: "file:///usr/share/icons/hicolor/scalable/apps/cubelinux-logo.svg"
                    sourceSize.width: 30
                    sourceSize.height: 30
                    fillMode: Image.PreserveAspectFit
                    Layout.preferredWidth: 30
                    Layout.preferredHeight: 30
                }
                Label {
                    text: i18n("cubelinux")
                    color: "#142B39"
                    font.bold: true
                    font.pointSize: 14
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: i18n("First-time setup")
                    color: "#5B7180"
                }
            }

            Label {
                text: i18n("cubelinux setup")
                color: "#1875A4"
                font.bold: true
                font.letterSpacing: 1.2
                Layout.fillWidth: true
            }

            Label {
                text: i18n("A fresh start. Your own space.")
                color: "#142B39"
                font.pointSize: 25
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            Label {
                text: i18n("Create a username and password to finish setting up cubelinux.")
                color: "#5B7180"
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Repeater {
                    model: [i18n("1  Network"), i18n("2  Language & keyboard"), i18n("3  Username & login")]
                    delegate: Label {
                        required property string modelData
                        text: modelData
                        color: modelData.startsWith("3") ? "#1875A4" : "#5B7180"
                        font.bold: modelData.startsWith("3")
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: accountInfo.implicitHeight + Kirigami.Units.largeSpacing * 2
                radius: 8
                color: "#F7FAFC"
                border.color: "#A6C1CE"

                ColumnLayout {
                    id: accountInfo
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.largeSpacing
                    spacing: Kirigami.Units.smallSpacing

                    Label {
                        text: i18n("Administrator access enabled for testing")
                        color: "#142B39"
                        font.bold: true
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    Label {
                        text: i18n("TEST BUILD · This first account is in the wheel group.")
                        color: "#8F4662"
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }

            Kirigami.FormLayout {
                Layout.fillWidth: true

                TextField {
                    id: usernameField
                    Kirigami.FormData.label: i18n("Username")
                    placeholderText: i18n("Choose a username")
                    inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
                    enabled: !AccountController.isUsernameFixed

                    Binding on text {
                        when: AccountController.isUsernameFixed
                        value: AccountController.username
                    }
                    Binding {
                        target: AccountController
                        property: "username"
                        value: usernameField.text
                        when: !AccountController.isUsernameFixed
                    }
                    Binding {
                        target: AccountController
                        property: "fullName"
                        value: usernameField.text
                    }
                }

                Kirigami.InlineMessage {
                    Layout.fillWidth: true
                    type: Kirigami.MessageType.Error
                    text: root.usernameMessage
                    visible: usernameField.text.length > 0 && root.usernameMessage.length > 0
                }

                Kirigami.PasswordField {
                    id: passwordField
                    Kirigami.FormData.label: i18n("Password")
                    placeholderText: i18n("Create a password")
                    Binding {
                        target: AccountController
                        property: "password"
                        value: passwordField.text
                    }
                    onAccepted: {
                        if (root.nextEnabled) {
                            root.nextRequested()
                        }
                    }
                }
            }

            Label {
                text: i18n("Your first account is used to sign in to this device.")
                color: "#5B7180"
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            Item { Layout.fillHeight: true }
        }
    }
}
