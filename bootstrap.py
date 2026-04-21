#!/usr/bin/env python3
"""Bootstrap dev tools: Homebrew, gh, uv, then install flctl from a GitHub release wheel."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "abx-ltd/python.flctl"
_RELEASE_TAG_ENV = "RELEASE_TAG"

_BREW_CANDIDATES = (
    "/opt/homebrew/bin/brew",
    "/usr/local/bin/brew",
)


def _find_brew() -> str | None:
    path = shutil.which("brew")
    if path:
        return path
    for candidate in _BREW_CANDIDATES:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _prepend_path(*dirs: str) -> None:
    parts = [d for d in dirs if os.path.isdir(d)]
    if not parts:
        return
    current = os.environ.get("PATH", "")
    os.environ["PATH"] = os.pathsep.join(parts + ([current] if current else []))


def _ensure_brew() -> str:
    brew = _find_brew()
    if not brew:
        print(
            "Homebrew not found. Install it from https://brew.sh and ensure `brew` is on your PATH.",
            file=sys.stderr,
        )
        sys.exit(1)
    return brew


def _ensure_brew_package(brew: str, command: str, formula: str) -> None:
    if shutil.which(command):
        return
    subprocess.run([brew, "install", formula], check=True)
    _prepend_path("/opt/homebrew/bin", "/usr/local/bin")
    if not shutil.which(command):
        print(
            f"`{command}` is still not on PATH after `brew install {formula}`. "
            "Add Homebrew’s bin directory to PATH and retry.",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    brew = _ensure_brew()
    _ensure_brew_package(brew, "gh", "gh")
    _ensure_brew_package(brew, "uv", "uv")

    subprocess.run(["gh", "auth", "login"], check=True)

    release_tag = os.environ.get(_RELEASE_TAG_ENV, "").strip()
    release_label = release_tag if release_tag else "latest release"

    with tempfile.TemporaryDirectory(prefix="flctl-download.") as download_dir:
        gh_download = ["gh", "release", "download"]
        if release_tag:
            gh_download.append(release_tag)            
        gh_download.extend(
            [
                "--repo",
                REPO,
                "--pattern",
                "*.whl",
                "-D",
                download_dir,
            ]
        )
        subprocess.run(gh_download, check=True)
        wheels = sorted(Path(download_dir).glob("*.whl"))
        if not wheels:
            print(
                f"No .whl assets matched *.whl for {release_label} in {REPO}.",
                file=sys.stderr,
            )
            sys.exit(1)
        if len(wheels) > 1:
            names = ", ".join(p.name for p in wheels)
            print(
                f"Multiple wheels matched *.whl: {names}. "
                "Use a tighter release tag or pattern.",
                file=sys.stderr,
            )
            sys.exit(1)
        wheel_path = str(wheels[0])
        subprocess.run(["uv", "tool", "install", "-U", wheel_path], check=True)


if __name__ == "__main__":
    main()
