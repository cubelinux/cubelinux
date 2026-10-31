# cubelinux

The cubelinux monorepo contains the bootc image builder, updater, and VShell.
Each project keeps its own source and component manifest in a top-level folder.

```text
cubelinux/
|-- cubelinux-image/
|-- cubelinux-updater/
`-- cubelinux-vshell/
```

The GitHub Actions image workflow runs when any of these project folders
changes. It stages updater and VShell files from the local component folders,
builds the image, verifies the result, and publishes it to GHCR.

See [the image-builder README](cubelinux-image/README.md),
[the updater README](cubelinux-updater/README.md), and
[the VShell README](cubelinux-vshell/README.md) for project-specific details.
