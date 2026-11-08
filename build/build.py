"""Build the Windows package of Transcribe: dist/Transcribe/ and dist/Transcribe-<version>-windows.zip.

    python build/build.py [--version 1.2.0]

Run it on Windows in a virtual environment with app/transcribe/requirements.txt and
pyinstaller installed. The GitHub workflow .github/workflows/release.yml uses the same script.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "transcribe"
BUILD = ROOT / "build"
DIST = ROOT / "dist"
NAME = "Transcribe"


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run_pyinstaller():
    import PyInstaller.__main__  # pylint: disable=import-outside-toplevel
    PyInstaller.__main__.run([
        str(BUILD / "launcher.py"),
        "--name", NAME,
        "--noconfirm", "--clean",
        "--distpath", str(DIST),
        "--workpath", str(BUILD / "pyinstaller-work"),
        "--specpath", str(BUILD / "pyinstaller-work"),
        "--paths", str(ROOT),
        # The whole application, also the parts that are imported only when chosen.
        "--collect-submodules", "app",
        "--collect-submodules", "sdk",
        "--collect-submodules", "tsutils",
        "--collect-submodules", "custom_speech_recognition",
        # Packages that need their data files or DLLs.
        "--collect-data", "customtkinter",      # themes
        "--collect-data", "wordcloud",          # font and stop words
        "--collect-data", "faster_whisper",     # voice activity model
        "--collect-binaries", "ctranslate2",    # the speech to text engine
        "--collect-all", "soundfile",           # libsndfile
        "--collect-all", "_soundfile_data",
        # Optional engines that need PyTorch (several GB) stay out, even if installed here.
        "--exclude-module", "torch",
        "--exclude-module", "whisper",
        "--exclude-module", "funasr",
        "--exclude-module", "torchaudio",
    ])


def add_files(folder: Path, version: str):
    shutil.copy2(APP / "parameters.yaml", folder / "parameters.yaml")
    shutil.copy2(APP / "override.yaml", folder / "override.yaml")
    (folder / "version.txt").write_text(f"{version} ({git_hash()})", encoding="utf-8")
    (folder / "bin").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "bin" / "README.md", folder / "bin" / "README.md")
    shutil.copy2(ROOT / "LICENSE", folder / "LICENSE.txt")
    (folder / "README.txt").write_text(
        "Transcribe\n"
        "==========\n\n"
        "1. Double-click Transcribe.exe.\n"
        "2. The first time, the speech to text model is downloaded (an internet connection is needed once).\n"
        "3. To use an OpenAI API key, put it in override.yaml, for example:\n\n"
        "   OpenAI:\n"
        "     api_key: 'sk-...'\n\n"
        "More: https://github.com/samaliyan/transcribe\n",
        encoding="utf-8")


def make_zip(folder: Path, version: str) -> Path:
    target = DIST / f"{NAME}-{version}-windows.zip"
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, Path(NAME) / path.relative_to(folder))
    return target


def folder_size_mb(folder: Path) -> float:
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file()) / 1e6


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", default="dev", help="version written into the package, e.g. 1.2.0")
    args = parser.parse_args()
    version = args.version.lstrip("vV") or "dev"

    if sys.platform != "win32":
        print("Warning: the package only runs on Windows; build it on Windows.")
    run_pyinstaller()
    folder = DIST / NAME
    add_files(folder, version)
    archive = make_zip(folder, version)
    print(f"Package folder: {folder} ({folder_size_mb(folder):.0f} MB)")
    print(f"Zip: {archive} ({archive.stat().st_size / 1e6:.0f} MB)")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"zip={archive}\n")


if __name__ == "__main__":
    main()
