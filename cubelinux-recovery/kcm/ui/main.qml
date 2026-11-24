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
            text: qsTr("Erase your personal files, apps, and settings, then reinstall cubelinux.")
        }
        Controls.Label {
            visible: !kcm.available
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: kcm.availabilityMessage
        }
        Controls.Button {
            text: kcm.busy ? qsTr("Checking recovery…") : qsTr("Restart to Factory Reset")
            enabled: kcm.available && !kcm.busy
            onClicked: kcm.restartToRecovery()
        }
    }
}
