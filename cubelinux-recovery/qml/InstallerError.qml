import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    visibility: Window.FullScreen
    title: qsTr("cubelinux installer")
    color: "#f3f5f8"
    property string restartError: ""
    Connections {
        target: recoveryController
        function onRestartFailed(message) { window.restartError = message }
    }
    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 64, 680)
        spacing: 20
        Label {
            text: qsTr("The installer cannot start")
            font.pixelSize: 30
            font.bold: true
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
        Label {
            objectName: "installerErrorMessage"
            text: installerErrorText
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
        Label {
            text: qsTr("No disk changes have been made.")
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
        Label {
            visible: window.restartError.length > 0
            text: window.restartError
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
        Button {
            text: qsTr("Restart")
            highlighted: true
            onClicked: recoveryController.restart()
        }
    }
}
