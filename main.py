"""Run the source checkout without installing the Python package."""

import sys
from pathlib import Path


def run() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    from cubelinux_updater.main import main

    return main()


if __name__ == "__main__":
    raise SystemExit(run())
