#!/usr/bin/env python3
"""Cross-platform build entry point for the Python worker and Electron shell."""

from argparse import ArgumentParser
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "src" / "desktop"
RELEASE = DESKTOP / "release"


def run(*command: str, cwd: Path = ROOT) -> None:
    """Run one build step and stop immediately on a useful non-zero exit."""

    subprocess.run(command, cwd=cwd, check=True)


def build_worker() -> None:
    """Bundle the current platform's Python runtime for users without Python."""

    output = ROOT / "build" / "worker"
    output.mkdir(parents=True, exist_ok=True)
    data_argument = (
        f"{ROOT / 'src' / 'db' / 'migrations'}"
        f"{os.pathsep}src/db/migrations"
    )
    run(
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
        "--name", "prisma-worker", "--paths", str(ROOT), "--add-data", data_argument,
        "--distpath", str(output), "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build"), str(ROOT / "src" / "worker.py"),
    )


def package_script() -> str:
    return {"Windows": "package:win", "Darwin": "package:mac"}.get(
        platform.system(), "package:linux"
    )


def package_desktop(pnpm: str) -> None:
    """Package outside release so a running old unpacked app cannot lock the build."""

    staging = ROOT / "build" / f"electron-package-{os.getpid()}"
    run(
        pnpm, "--filter", "@prisma/desktop", package_script(),
        f"--config.directories.output={staging}",
    )
    artifacts = _package_artifacts(staging)
    if not artifacts:
        raise RuntimeError(f"Electron builder не создал установщик в {staging}")
    RELEASE.mkdir(parents=True, exist_ok=True)
    for artifact in artifacts:
        destination = RELEASE / artifact.name
        shutil.copy2(artifact, destination)
        print(f"Release artifact: {destination}")
    try:
        shutil.rmtree(staging)
    except OSError as error:
        # A scanner may briefly hold staging files; the installer is already safe.
        print(f"Warning: temporary package directory was not removed: {error}")


def _package_artifacts(staging: Path) -> list[Path]:
    """Return only distributable files, never the temporary unpacked application."""

    patterns = {
        "Windows": ("*.exe", "*.exe.blockmap"),
        "Darwin": ("*.dmg", "*.dmg.blockmap"),
    }.get(platform.system(), ("*.AppImage", "*.AppImage.blockmap"))
    return sorted({item for pattern in patterns for item in staging.glob(pattern)
                   if "__uninstaller" not in item.name})


def pnpm_executable() -> str:
    """Find pnpm on every platform or accept an explicit CI/runtime path."""

    configured = os.getenv("PRISMA_PNPM")
    discovered = shutil.which("pnpm") or shutil.which("pnpm.cmd")
    if configured or discovered:
        return configured or discovered or "pnpm"
    raise RuntimeError("pnpm не найден в PATH. Установите pnpm или задайте PRISMA_PNPM.")


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--skip-package", action="store_true")
    options = parser.parse_args()
    pnpm = pnpm_executable()

    if not options.skip_install:
        run(sys.executable, "-m", "pip", "install", "-e", ".[dev,desktop-build]")
        # A project-local store avoids machine-specific pnpm paths in node_modules.
        run(pnpm, "install", "--store-dir", str(ROOT / ".pnpm-store"))
    build_worker()
    run(pnpm, "desktop:build")
    if not options.skip_package:
        package_desktop(pnpm)


if __name__ == "__main__":
    main()
