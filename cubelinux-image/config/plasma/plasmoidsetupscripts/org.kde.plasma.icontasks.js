// Set the default taskbar launchers when Plasma creates the task manager.
var dolphinLauncher = "applications:org.kde.dolphin.desktop";

applet.currentConfigGroup = ["General"];
var launcherText = String(applet.readConfig("launchers", ""));
var launchers = launcherText ? launcherText.split(",") : [];
var cleanedLaunchers = [];
var hasDolphin = false;

for (var launcherIndex = 0; launcherIndex < launchers.length; launcherIndex++) {
    var launcher = launchers[launcherIndex].trim();
    if (!launcher) {
        continue;
    }
    if (launcher === "preferred://filemanager") {
        launcher = dolphinLauncher;
    }
    if (launcher === dolphinLauncher) {
        if (hasDolphin) {
            continue;
        }
        hasDolphin = true;
    }
    cleanedLaunchers.push(launcher);
}

if (!hasDolphin) {
    cleanedLaunchers.push(dolphinLauncher);
}

applet.writeConfig("launchers", cleanedLaunchers.join(","));
applet.reloadConfig();
