"""Linux application discovery. Other desktop adapters can reuse core.py."""

from .core import Action, Catalog, normalize
from .config import Routine


def discover_apps():
    from gi.repository import Gio
    apps = {}
    for app in Gio.AppInfo.get_all():
        if app.get_id() and app.should_show():
            apps[app.get_id()] = app
    return apps


def build_catalog(apps, routines: list[Routine]) -> Catalog:
    actions = []
    for app_id, app in apps.items():
        name = app.get_display_name()
        phrases = {normalize(name), f"open {normalize(name)}"}
        lower = name.casefold()
        # Friendly spoken names avoid punctuation and uncommon product names.
        for keyword, alias in [("firefox", "browser"), ("terminal", "terminal"),
                               ("intellij", "idea"), ("codex", "assistant"),
                               ("visual studio code", "code")]:
            if keyword in lower:
                phrases.add(f"open {alias}")
        actions.append(Action(app_id, name, "app", tuple(sorted(phrases))))
    for routine in routines:
        phrases = (routine.name, *routine.aliases, f"start {routine.name}")
        actions.append(Action(routine.name, routine.name, "routine", phrases))
    return Catalog(actions)


def launch_app(apps, app_id: str) -> str:
    app = apps.get(app_id)
    if app is None:
        raise ValueError(f"Application is not available: {app_id}")
    # Gio honors desktop-file launch semantics and Flatpak exports. Never shell-eval text.
    if not app.launch([], None):
        raise RuntimeError(f"Desktop rejected the launch request for {app.get_display_name()}.")
    return f"Launch requested: {app.get_display_name()}"
