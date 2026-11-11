"""Read and atomically save user-defined routines, separately from the UI."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile

from .core import normalize


@dataclass(frozen=True)
class Routine:
    name: str
    aliases: tuple[str, ...]
    app_ids: tuple[str, ...]


def config_path() -> Path:
    override = os.environ.get("ORBIT_CONFIG_PATH")
    if override:
        return Path(override)
    root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return root / "orbit" / "routines.json"


def read_routines(path: Path) -> list[Routine]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Unsupported routines file version. Expected version 1.")
    items = data.get("routines")
    if not isinstance(items, list):
        raise ValueError("'routines' must be a list.")
    routines: list[Routine] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Every routine must be an object.")
        name, aliases, apps = item.get("name"), item.get("aliases"), item.get("apps")
        if not isinstance(name, str) or not normalize(name):
            raise ValueError("Every routine needs an English name.")
        if normalize(name) in seen:
            raise ValueError(f"Duplicate routine: {name}")
        if not isinstance(aliases, list) or not all(isinstance(a, str) and normalize(a) for a in aliases):
            raise ValueError(f"Aliases for {name} must be a list of nonempty English phrases.")
        if not isinstance(apps, list) or not apps or not all(isinstance(a, str) and a.strip() for a in apps):
            raise ValueError(f"{name} needs at least one desktop application ID.")
        seen.add(normalize(name))
        routines.append(Routine(name, tuple(aliases), tuple(apps)))
    return routines


def save_routines(path: Path, routines: list[Routine]) -> None:
    data = {"version": 1, "routines": [
        {"name": r.name, "aliases": list(r.aliases), "apps": list(r.app_ids)}
        for r in routines
    ]}
    # Validate before replacing an existing user configuration.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".orbit-", suffix=".json", delete=False) as f:
            temporary = Path(f.name)
            json.dump(data, f, indent=2)
            f.write("\n")
        read_routines(temporary)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
