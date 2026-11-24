# cubelinux Recovery

This directory contains the factory reset wizard under development. The
interface is not yet connected to a reset backend. The image includes the
prototype, but recovery boot does not launch it yet.
It must not be used to claim that factory reset is available.

## Static UI preview

With PySide6 installed, run `python cubelinux-recovery/preview.py` from the
`cubelinux` repository. The window demonstrates the proposed recovery flow
using example progress and does not access disks or perform a reset. It loads
the same QML as the recovery application with a simulated controller. The real
application is not yet connected to a reset backend.
