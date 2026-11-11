"""Persistent, per-user activation and standard XDG login startup."""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile

APP_ID = "io.github.masoudrw1.Orbit"


@dataclass(frozen=True)
class Preferences:
    enabled: bool = False
    start_at_login: bool = False


def preferences_path() -> Path:
    override = os.environ.get("ORBIT_SETTINGS_PATH")
    if override:
        return Path(override)
    root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return root / "orbit" / "settings.json"


def autostart_path() -> Path:
    override = os.environ.get("ORBIT_AUTOSTART_DIR")
    root = Path(override) if override else Path(
        os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "autostart"
    return root / f"{APP_ID}.desktop"


def read_preferences(path: Path | None = None) -> Preferences:
    path = path or preferences_path()
    if not path.exists():
        return Preferences()
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("version") != 1 or
            type(data.get("enabled")) is not bool or
            type(data.get("start_at_login")) is not bool):
        raise ValueError("Orbit activation settings are invalid. Expected version 1 and boolean settings.")
    if data["start_at_login"] and not data["enabled"]:
        raise ValueError("Login startup requires Orbit to be activated.")
    return Preferences(data["enabled"], data["start_at_login"])


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".orbit-", delete=False) as output:
            temporary = Path(output.name)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def desktop_entry(launcher: Path) -> str:
    launcher = launcher.resolve()
    value = str(launcher)
    if any(c in value for c in "\n\r\x00"):
        raise ValueError("Invalid launcher path.")
    # Desktop Exec quoting follows the Desktop Entry specification, not shell eval.
    quoted = value.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$").replace("%", "%%")
    return ("[Desktop Entry]\nType=Application\nName=Orbit\n"
            "Comment=Listen for Hey Orbit after sign-in\n"
            f'Exec="{quoted}" --background\n'
            f"TryExec={value.replace(chr(92), chr(92) * 2)}\n"
            "Terminal=false\nX-GNOME-Autostart-enabled=true\n")


def apply_preferences(preferences: Preferences, launcher: Path,
                      settings_file: Path | None = None,
                      startup_file: Path | None = None) -> None:
    """Update login entry first, then commit settings; roll back on write failure."""
    if type(preferences.enabled) is not bool or type(preferences.start_at_login) is not bool:
        raise ValueError("Activation settings must be booleans.")
    if preferences.start_at_login and not preferences.enabled:
        raise ValueError("Login startup requires activation.")
    settings_file = settings_file or preferences_path()
    startup_file = startup_file or autostart_path()
    previous = startup_file.read_text(encoding="utf-8") if startup_file.exists() else None
    try:
        if preferences.start_at_login:
            if not launcher.is_file() or not os.access(launcher, os.X_OK):
                raise ValueError("Orbit's launcher is unavailable. Reinstall the app before enabling login startup.")
            _atomic_write(startup_file, desktop_entry(launcher))
        else:
            startup_file.unlink(missing_ok=True)
        data = {"version": 1, **asdict(preferences)}
        _atomic_write(settings_file, json.dumps(data, indent=2) + "\n")
    except (OSError, ValueError):
        if previous is not None:
            _atomic_write(startup_file, previous)
        else:
            startup_file.unlink(missing_ok=True)
        raise


def launcher_path() -> Path:
    override = os.environ.get("ORBIT_LAUNCHER")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "run.sh"
