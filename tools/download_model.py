#!/usr/bin/env python3
"""Explicit, bounded download of the official Apache-2.0 English Vosk model."""

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tempfile
import urllib.request
import zipfile

NAME = "vosk-model-small-en-us-0.15"
URL = f"https://alphacephei.com/vosk/models/{NAME}.zip"


def validate_archive(archive: zipfile.ZipFile):
    total = 0
    for entry in archive.infolist():
        parts = PurePosixPath(entry.filename).parts
        if (not parts or parts[0] != NAME or ".." in parts or
                PurePosixPath(entry.filename).is_absolute() or
                stat.S_ISLNK(entry.external_attr >> 16)):
            raise ValueError("Unexpected path in model archive.")
        total += entry.file_size
    if total > 200 * 1024 * 1024:
        raise ValueError("Extracted model exceeds the expected size limit.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parents[1] / ".models")
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    target = args.directory / NAME
    if (target / "am" / "final.mdl").is_file():
        print(f"Model is already available: {target}")
        return
    if target.exists():
        raise SystemExit(f"Incomplete model already exists at {target}; move it aside and retry.")
    print(f"Downloading the ~40 MB English model from {URL}")
    with tempfile.TemporaryDirectory(prefix=".orbit-model-", dir=args.directory) as directory:
        staging = Path(directory)
        archive_path = staging / "model.zip"
        digest = hashlib.sha256()
        size = 0
        # curl also understands desktop ALL_PROXY / SOCKS proxy settings that
        # Python's urllib does not support. Both paths use the same official URL.
        if shutil.which("curl"):
            subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error",
                            "--retry", "2", "--connect-timeout", "15", "--max-time", "300",
                            "--max-filesize", str(80 * 1024 * 1024),
                            "--output", str(archive_path), URL], check=True)
        else:
            with urllib.request.urlopen(URL, timeout=60) as response, archive_path.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > 80 * 1024 * 1024:
                        raise ValueError("Download exceeded the expected size limit.")
                    output.write(chunk)
        size = 0
        with archive_path.open("rb") as downloaded:
            while chunk := downloaded.read(1024 * 1024):
                size += len(chunk)
                if size > 80 * 1024 * 1024:
                    raise ValueError("Download exceeded the expected size limit.")
                digest.update(chunk)
        with zipfile.ZipFile(archive_path) as archive:
            validate_archive(archive)
            archive.extractall(staging)
        model = staging / NAME
        if not (model / "am" / "final.mdl").is_file():
            raise ValueError("Downloaded archive is not the expected model.")
        model.rename(target)
        (args.directory / f"{NAME}.download-sha256.txt").write_text(digest.hexdigest() + "\n")
    print(f"Model ready: {target}")
    print("SHA-256 recorded for this download; it is not an upstream published checksum.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        raise SystemExit(f"Model setup failed: {exc}. Check the connection and retry; no model was installed.")
