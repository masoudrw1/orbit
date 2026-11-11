#!/usr/bin/env python3
"""Build the Pop!_OS/Ubuntu 24.04 amd64 alpha installer, without sudo.

No developer venv, user settings or source-checkout path is included. Use --fetch
explicitly to populate the build cache from pinned official URLs. Later builds
use the verified cache offline. Standard Python dependencies are declared to APT.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def file_hash(path: Path, algorithm="sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Unexpected symlink in model: {path}")
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode() + b"\0")
            digest.update(bytes.fromhex(file_hash(path)))
    return digest.hexdigest()


def cached_asset(asset: dict, cache: Path, fetch: bool) -> Path:
    target = cache / asset["filename"]
    if not target.exists():
        if not fetch:
            raise ValueError(f"Missing {target.name}. Run the builder once with --fetch.")
        cache.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".part")
        try:
            subprocess.run(["curl", "-fLsS", "--connect-timeout", "15", "--max-time", "300",
                            "--max-filesize", str(100 * 1024 * 1024),
                            "--output", str(temporary), asset["url"]], check=True)
            if file_hash(temporary) != asset["sha256"]:
                raise ValueError(f"Checksum mismatch for {target.name}.")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    if file_hash(target) != asset["sha256"]:
        raise ValueError(f"Cached asset has changed: {target}. Move it aside and fetch again.")
    return target


def extract_vosk(wheel: Path, target: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Invalid wheel path.")
            if path.parts and (path.parts[0] == "vosk" or path.parts[0].startswith("vosk-0.3.45.dist-info")):
                archive.extract(item, target)


def debian_version(version: str) -> str:
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:a\d+)?", version):
        raise ValueError("Unsupported project version for this alpha builder.")
    return re.sub(r"a(\d+)$", r"~alpha\1", version) + "-1"


def source_receipt() -> dict:
    files = [*ROOT.joinpath("orbit").glob("*.py"), ROOT / "orbit/style.css",
             *ROOT.joinpath("packaging").rglob("*"), Path(__file__)]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(files) if p.is_file()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="Download missing pinned build assets")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--cache", type=Path, default=ROOT / ".build-assets")
    parser.add_argument("--model", type=Path, default=ROOT / ".models/vosk-model-small-en-us-0.15")
    args = parser.parse_args()
    if platform.machine() != "x86_64":
        parser.error("This alpha installer targets amd64 only.")
    for program in ["dpkg-deb", *( ["curl"] if args.fetch else [])]:
        if not shutil.which(program):
            parser.error(f"Required build tool is missing: {program}")
    assets = json.loads((ROOT / "packaging/assets.json").read_text())
    if not args.model.is_dir() and args.fetch:
        subprocess.run([sys.executable, str(ROOT / "tools/download_model.py"),
                        "--directory", str(args.model.parent)], check=True)
    if not args.model.is_dir() or tree_hash(args.model) != assets["model"]["tree_sha256"]:
        parser.error("The pinned English model is missing or modified. Run tools/download_model.py and use the original model directory.")
    wheel = cached_asset(assets["vosk"], args.cache, args.fetch)
    native_packages = [cached_asset(item, args.cache, args.fetch) for item in assets["native"]]
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    version = debian_version(version)
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output.resolve() / f"orbit-launcher_{version}_amd64.deb"
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1794438000"))
    with tempfile.TemporaryDirectory(prefix="orbit-deb-") as temporary:
        stage = Path(temporary) / "root"
        app = stage / "opt/orbit"
        app.mkdir(parents=True)
        shutil.copytree(ROOT / "orbit", app / "app/orbit",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        extract_vosk(wheel, app / "python")
        shutil.copytree(args.model, app / "models" / assets["model"]["name"])
        docs = stage / "usr/share/doc/orbit-launcher"
        docs.mkdir(parents=True)
        for source, destination in [(ROOT / "LICENSE", "copyright"),
                                    (ROOT / "packaging/THIRD_PARTY.md", "THIRD_PARTY.md"),
                                    (ROOT / "docs/INSTALL.md", "INSTALL.md")]:
            shutil.copy2(source, docs / destination)
        native = Path(temporary) / "native"
        for package in native_packages:
            subprocess.run(["dpkg-deb", "--extract", str(package), str(native)], check=True)
        shutil.copytree(native / "usr/lib/x86_64-linux-gnu", app / "native/lib", symlinks=True)
        shutil.copytree(native / "usr/share/doc", docs / "third-party", symlinks=True)
        shutil.copytree(ROOT / "packaging/licenses", docs / "third-party/licenses")
        (app / "bin").mkdir()
        shutil.copy2(ROOT / "packaging/launch-orbit.sh", app / "bin/orbit")
        (app / "bin/orbit").chmod(0o755)
        (stage / "usr/bin").mkdir(parents=True)
        (stage / "usr/bin/orbit").symlink_to("../../opt/orbit/bin/orbit")
        for source, destination in [
            (ROOT / "packaging/orbit.desktop", stage / "usr/share/applications" / "io.github.masoudrw1.Orbit.desktop"),
            (ROOT / "packaging/orbit.svg", stage / "usr/share/icons/hicolor/scalable/apps/io.github.masoudrw1.Orbit.svg"),
        ]:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        receipt = {"version": version, "target": "Pop!_OS/Ubuntu 24.04 amd64", "assets": assets,
                   "source_sha256": source_receipt(), "source_date_epoch": epoch}
        (docs / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        control = stage / "DEBIAN"
        control.mkdir()
        size = sum(p.stat().st_size for p in stage.rglob("*") if p.is_file() and not p.is_symlink())
        (control / "control").write_text(
            f"Package: orbit-launcher\nVersion: {version}\nArchitecture: amd64\n"
            "Maintainer: masoudrw1 <masoudrw1@users.noreply.github.com>\n"
            "Section: utils\nPriority: optional\n"
            f"Installed-Size: {(size + 1023) // 1024}\n"
            "Depends: python3 (>= 3.12), python3 (<< 3.13), python3-gi, gir1.2-gtk-4.0 (>= 4.10), "
            "libgtk-4-1 (>= 4.10), libglib2.0-0t64 (>= 2.80), libwayland-client0, "
            "libc6 (>= 2.34), libstdc++6, libgcc-s1, pulseaudio-utils, "
            "python3-cffi, python3-requests, python3-srt, python3-tqdm, python3-websockets\n"
            "Homepage: https://github.com/masoudrw1/orbit\n"
            "Description: English voice and keyboard launcher for Linux\n"
            " Activate Hey Orbit once, then call it to reveal the launcher.\n"
            " Includes the offline English speech model and a private Layer Shell runtime.\n"
            " Native island target: COSMIC on Wayland. GNOME uses a regular window.\n"
        )
        sums = []
        for path in sorted(stage.rglob("*")):
            if path.is_dir():
                path.chmod(0o755)
            elif path.is_file() and not path.is_symlink():
                if path != app / "bin/orbit":
                    path.chmod(0o644)
                if control not in path.parents:
                    sums.append(f"{file_hash(path, 'md5')}  {path.relative_to(stage).as_posix()}")
        (control / "md5sums").write_text("\n".join(sums) + "\n")
        for path in [stage, *stage.rglob("*")]:
            os.utime(path, (epoch, epoch), follow_symlinks=False)
        build_env = {**os.environ, "SOURCE_DATE_EPOCH": str(epoch)}
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(stage), str(output)],
                       check=True, env=build_env)
    checksum = file_hash(output)
    output.with_suffix(output.suffix + ".sha256").write_text(f"{checksum}  {output.name}\n")
    print(f"Built: {output}\nSHA-256: {checksum}")
    print("This built the installer; it did not install it, activate the microphone, or enable login startup.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Orbit package build failed: {exc}")
