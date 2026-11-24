import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    width: 980; height: 650; minimumWidth: 760; minimumHeight: 520
    visibility: recoveryController.preview ? Window.Windowed : Window.FullScreen
    visible: true; color: "#f3f5f8"; title: "cubelinux Recovery"
    property int page: 0
    readonly property var labels: ["Factory Reset", "Confirm", "Resetting", "Complete"]
    readonly property var titles: ["Reset your system", "Confirm factory reset", "Resetting cubelinux", "Factory reset complete"]
    readonly property var descriptions: [
        "Reinstall cubelinux and remove your personal files, apps, and settings. You can reset without an internet connection.",
        "All personal files, apps, and settings on this cubelinux installation will be erased. This cannot be undone.",
        "Please keep your computer powered on while cubelinux is reinstalled.",
        "Restart your computer to begin setting up cubelinux again."
    ]
    Dialog {
        id: restartNotice
        anchors.centerIn: parent
        title: qsTr("Restart")
        modal: true
        standardButtons: Dialog.Ok
        Label { text: qsTr("The computer would restart in a completed recovery system."); wrapMode: Text.Wrap; width: 340 }
    }
    RowLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.fillHeight: true; Layout.preferredWidth: 220; color: "#202c42"
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 26; spacing: 24
                Label { text: "cubelinux"; color: "white"; font.pixelSize: 22; font.bold: true }
                Label { text: "RECOVERY"; color: "#a6b3c8"; font.pixelSize: 11; font.bold: true }
                Repeater {
                    model: root.labels
                    Label {
                        required property int index
                        required property string modelData
                        text: (index + 1) + "   " + modelData
                        color: index === root.page ? "white" : "#a6b3c8"
                        font.bold: index === root.page
                    }
                }
                Item { Layout.fillHeight: true }
                Label { text: "OFFLINE RECOVERY"; color: "#a6b3c8"; font.pixelSize: 11 }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.margins: 44; spacing: 18
            Label { text: "RECOVERY"; color: "#59759e"; font.bold: true; font.pixelSize: 11 }
            Label { text: root.titles[root.page]; font.pixelSize: 30; font.bold: true; color: "#1c293d"; Layout.fillWidth: true; wrapMode: Text.Wrap }
            Label { text: root.descriptions[root.page]; color: "#53637a"; font.pixelSize: 15; Layout.fillWidth: true; wrapMode: Text.Wrap }
            Rectangle {
                Layout.fillWidth: true; Layout.topMargin: 16
                implicitHeight: details.implicitHeight + 40; radius: 12; color: "white"; border.color: "#dce3ed"
                ColumnLayout {
                    id: details; anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.margins: 20; spacing: 10
                    Label { text: ["Before you continue", "This will erase your data", "Example progress", "Next step"][root.page]; font.bold: true; font.pixelSize: 16 }
                    Label { text: ["Back up any files you want to keep.", "Your personal files, apps, and settings will be removed.", "Reinstalling the system image…", "Complete the first-time setup after restarting."][root.page]; color: "#53637a"; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    ProgressBar { visible: root.page === 2; value: 0.62; Layout.fillWidth: true }
                }
            }
            Item { Layout.fillHeight: true }
            Label { text: "Visual demo only · no disks are changed"; color: "#68798d" }
            RowLayout {
                Layout.fillWidth: true
                Button { text: "Back"; enabled: root.page > 0; onClicked: root.page-- }
                Item { Layout.fillWidth: true }
                Button { text: root.page === 3 ? "Restart" : root.page === 1 ? "Factory Reset" : "Next"; highlighted: true; enabled: root.page !== 1 || recoveryController.preview; onClicked: { if (root.page === 3) restartNotice.open(); else root.page++ } }
            }
        }
    }
}
