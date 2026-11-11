"""Entry point: python -m orbit. GTK is imported only when the UI is requested."""

import argparse
import importlib.util
from importlib import import_module
import json
import os
from pathlib import Path
import shutil
import sys


def default_model() -> Path:
    if override := os.environ.get("ORBIT_MODEL_DIR"):
        return Path(override)
    return Path(__file__).resolve().parent.parent / ".models" / "vosk-model-small-en-us-0.15"


def doctor(model: Path) -> int:
    from .activation import autostart_path, read_preferences
    checks = {
        "python": sys.version.split()[0],
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
        "session": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "gtk_python": importlib.util.find_spec("gi") is not None,
        "voice_package": False,
        "microphone_recorder": shutil.which("parec") is not None,
        "english_model": (model / "am" / "final.mdl").is_file(),
    }
    try:
        import_module("vosk")
        checks["voice_package"] = True
    except (ImportError, OSError) as exc:
        checks["voice_error"] = str(exc)
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        checks["gtk4"] = True
        gi.require_version("Gtk4LayerShell", "1.0")
        checks["layer_shell_typelib"] = True
    except (ImportError, ValueError):
        checks["layer_shell_typelib"] = False
    try:
        settings = read_preferences()
        checks["activated"] = settings.enabled
        checks["start_at_login"] = settings.start_at_login and autostart_path().is_file()
    except (ValueError, OSError) as exc:
        checks["activation_error"] = str(exc)
    print(json.dumps(checks, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Orbit · English voice and keyboard launcher")
    parser.add_argument("--doctor", action="store_true", help="Report available dependencies without opening a microphone")
    parser.add_argument("--window", action="store_true", help="Use a normal window (development / GNOME fallback)")
    parser.add_argument("--model", type=Path, default=default_model(), help="Path to the offline Vosk English model directory")
    lifecycle = parser.add_mutually_exclusive_group()
    lifecycle.add_argument("--background", action="store_true", help="Resume saved activation hidden (used at sign-in)")
    lifecycle.add_argument("--quit", action="store_true", help="Quit the running Orbit instance")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.doctor:
        return doctor(args.model)
    try:
        from .ui import run
        return run(args.model, args.window, args.smoke_test, args.background, args.quit)
    except (ImportError, ValueError, RuntimeError) as exc:
        print(f"Orbit could not start: {exc}\nSee docs/START_HERE_FA.md for setup.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
