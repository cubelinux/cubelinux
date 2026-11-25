import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kcmutils as KCM
import org.kde.kirigami as Kirigami

KCM.SimpleKCM {
    Controls.Dialog {
        id: errorDialog
        title: qsTr("Could not restart into recovery")
        modal: true
        standardButtons: Controls.Dialog.Ok
        property string message: ""
        Controls.Label { text: errorDialog.message; wrapMode: Text.Wrap; width: 360 }
    }
    Connections {
        target: kcm
        function onRestartFailed(message) { errorDialog.message = message; errorDialog.open() }
    }
    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing
        Kirigami.Heading { text: qsTr("Factory Reset"); level: 2 }
        Controls.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: qsTr("Reinstall cubelinux from the recovery image stored on this device.")
        }
        Kirigami.InlineMessage {
            Layout.fillWidth: true
            type: Kirigami.MessageType.Warning
            showCloseButton: false
            text: qsTr("Factory Reset erases all files, accounts, apps, and settings on the installed system. This cannot be undone.")
        }
        Controls.Label {
            visible: !kcm.available
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: kcm.availabilityMessage
        }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            Controls.Button {
                text: kcm.busy ? qsTr("Checking recovery...") : qsTr("Restart to Factory Reset")
                enabled: kcm.available && !kcm.busy
                onClicked: kcm.restartToRecovery()
            }
            Item { Layout.fillWidth: true }
        }
    }
}
