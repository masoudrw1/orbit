"""GTK presentation adapter. All command matching lives in core.py."""

import ctypes
import ctypes.util
from pathlib import Path
import os
import sys

# Layer Shell must be linked before GTK initializes the Wayland connection.
_layer_library = None
_layer_error = "Layer Shell is not installed"
try:
    path = ctypes.util.find_library("gtk4-layer-shell") or "libgtk4-layer-shell.so.0"
    _layer_library = ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
except OSError:
    pass

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk

LayerShell = None
if _layer_library:
    try:
        gi.require_version("Gtk4LayerShell", "1.0")
        from gi.repository import Gtk4LayerShell as LayerShell
    except (ImportError, ValueError):
        _layer_error = "Layer Shell introspection files are missing"

from .config import Routine, config_path, read_routines, save_routines
from .desktop import build_catalog, discover_apps, launch_app
from .voice import VoiceListener


class OrbitApp(Gtk.Application):
    def __init__(self, model: Path, window_mode: bool, smoke_test: bool):
        super().__init__(application_id="io.github.orbit.launcher",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.model, self.window_mode, self.smoke_test = model, window_mode, smoke_test
        self.window = None
        self.listener = None
        self.voice_epoch = 0
        self.updating_switch = False
        self.selected_apps: list[str] = []
        self.expanded = True
        self.busy = False

    def do_activate(self):
        if self.window:
            self.window.present()
            return
        self.apps = discover_apps()
        self.path = config_path()
        config_error = None
        try:
            self.routines = read_routines(self.path)
        except (ValueError, OSError) as exc:
            self.routines = []
            config_error = f"Could not read routines: {exc}. Fix the file before saving."
        self.config_error = config_error
        self.catalog = build_catalog(self.apps, self.routines)

        provider = Gtk.CssProvider()
        provider.load_from_path(str(Path(__file__).with_name("style.css")))
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window = Gtk.ApplicationWindow(application=self, title="Orbit")
        self.window.set_decorated(False)
        self.window.add_css_class("orbit-window")
        self.is_island = bool(not self.window_mode and LayerShell and LayerShell.is_supported())
        if self.is_island:
            LayerShell.init_for_window(self.window)
            LayerShell.set_namespace(self.window, "orbit")
            LayerShell.set_layer(self.window, LayerShell.Layer.OVERLAY)
            LayerShell.set_anchor(self.window, LayerShell.Edge.TOP, True)
            LayerShell.set_margin(self.window, LayerShell.Edge.TOP, 38)
            LayerShell.set_exclusive_zone(self.window, 0)
            LayerShell.set_keyboard_mode(self.window, LayerShell.KeyboardMode.ON_DEMAND)
        self.window.connect("close-request", self.on_close)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_key)
        self.window.add_controller(keys)

        self.stack = Gtk.Stack()
        self.stack.set_hhomogeneous(False)
        self.stack.set_vhomogeneous(False)
        self.stack.set_interpolate_size(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(180)
        if self.smoke_test:
            # Capture a settled widget tree; compositor frame timing varies in CI.
            self.stack.set_transition_duration(0)
        self.stack.add_css_class("island")
        self.window.set_child(self.stack)

        compact = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        compact.set_size_request(250, 56)
        compact.add_css_class("compact")
        compact_button = Gtk.Button(label="◉   Orbit")
        compact_button.add_css_class("flat")
        compact_button.set_hexpand(True)
        compact_button.connect("clicked", lambda *_: self.expand())
        compact.append(compact_button)
        self.compact_status = Gtk.Label(label="Ready")
        self.compact_status.add_css_class("muted")
        compact.append(self.compact_status)
        self.stack.add_named(compact, "compact")

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        panel.set_size_request(550, -1)
        panel.add_css_class("panel")
        self.stack.add_named(panel, "expanded")
        header = Gtk.Box(spacing=10)
        logo = Gtk.Label(label="◉")
        logo.add_css_class("logo")
        header.append(logo)
        title = Gtk.Label(label="Orbit", xalign=0)
        title.add_css_class("title")
        title.set_hexpand(True)
        header.append(title)
        badge = Gtk.Label(label="EARLY ALPHA")
        badge.add_css_class("badge")
        header.append(badge)
        for label, callback in [("−", lambda *_: self.collapse()), ("×", lambda *_: self.window.close())]:
            button = Gtk.Button(label=label)
            button.add_css_class("flat")
            button.connect("clicked", callback)
            header.append(button)
        panel.append(header)
        self.search = Gtk.SearchEntry(placeholder_text="Search apps or type a routine…")
        self.search.connect("search-changed", self.refresh_results)
        self.search.connect("activate", self.on_enter)
        panel.append(self.search)

        self.results = Gtk.ListBox()
        self.results.add_css_class("results")
        self.results.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.results.connect("row-activated", lambda _, row: self.execute(row.action))
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(220)
        scroll.set_max_content_height(220)
        scroll.set_child(self.results)
        panel.append(scroll)

        builder = Gtk.Expander(label="Build your first routine")
        form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.routine_name = Gtk.Entry(placeholder_text="Routine name, e.g. Programming")
        self.routine_aliases = Gtk.Entry(placeholder_text="Spoken aliases, e.g. start coding, work mode")
        self.selected_label = Gtk.Label(label="Use + beside an app to add it.", xalign=0, wrap=True)
        form.append(self.routine_name)
        form.append(self.routine_aliases)
        form.append(self.selected_label)
        buttons = Gtk.Box(spacing=8)
        save = Gtk.Button(label="Save routine")
        save.add_css_class("suggested-action")
        save.connect("clicked", self.save_routine)
        clear = Gtk.Button(label="Clear selection")
        clear.connect("clicked", self.clear_selection)
        buttons.append(save)
        buttons.append(clear)
        form.append(buttons)
        builder.set_child(form)
        panel.append(builder)

        footer = Gtk.Box(spacing=10)
        self.voice_button = Gtk.ToggleButton(label="Enable voice")
        self.voice_button.connect("toggled", self.toggle_voice)
        footer.append(self.voice_button)
        mode = Gtk.Label(label="COSMIC island" if self.is_island else "Window mode")
        mode.add_css_class("muted")
        mode.set_hexpand(True)
        mode.set_xalign(1)
        footer.append(mode)
        panel.append(footer)
        self.status = Gtk.Label(label="", xalign=0, wrap=True)
        self.status.add_css_class("status")
        self.status.set_max_width_chars(60)
        panel.append(self.status)
        self.refresh_results()
        if config_error:
            self.set_status(config_error)
        elif not self.is_island:
            self.set_status("Development window · Install Layer Shell for the anchored island. Voice starts only when enabled.")
        else:
            self.set_status("Search an app, build a routine, or enable offline voice.")
        self.stack.set_visible_child_name("expanded")
        self.window.present()
        if self.smoke_test:
            GLib.timeout_add(250, self._smoke_collapse)
            GLib.timeout_add(500, self._smoke_expand)
            GLib.timeout_add(850, self._snapshot)
            GLib.timeout_add(1200, self._smoke_quit)

    def set_status(self, text: str):
        self.status.set_text(text)

    def refresh_results(self, *_):
        while row := self.results.get_first_child():
            self.results.remove(row)
        for action in self.catalog.search(self.search.get_text()):
            row = Gtk.ListBoxRow()
            row.action = action
            box = Gtk.Box(spacing=12)
            box.add_css_class("result")
            icon = Gtk.Image()
            icon.set_pixel_size(28)
            if action.kind == "app" and self.apps[action.identifier].get_icon():
                icon.set_from_gicon(self.apps[action.identifier].get_icon())
            else:
                icon.set_from_icon_name("view-grid-symbolic")
            box.append(icon)
            names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            names.set_hexpand(True)
            name = Gtk.Label(label=action.title, xalign=0)
            name.add_css_class("result-title")
            names.append(name)
            description = Gtk.Label(label="Routine" if action.kind == "routine" else "Application", xalign=0)
            description.add_css_class("muted")
            names.append(description)
            box.append(names)
            if action.kind == "app":
                add = Gtk.Button(label="+")
                add.add_css_class("flat")
                add.set_tooltip_text("Add to your routine")
                add.connect("clicked", lambda _, app_id=action.identifier: self.add_selection(app_id))
                box.append(add)
            row.set_child(box)
            self.results.append(row)
        if first := self.results.get_row_at_index(0):
            self.results.select_row(first)

    def on_enter(self, *_):
        if row := self.results.get_selected_row():
            self.execute(row.action)
        else:
            self.set_status("No matching app or routine.")

    def execute(self, action):
        if self.busy:
            self.set_status("A routine is already launching. Please wait.")
            return
        if action.kind == "app":
            try:
                self.set_status(launch_app(self.apps, action.identifier))
            except Exception as exc:
                self.set_status(str(exc))
            return
        routine = next(r for r in self.routines if r.name == action.identifier)
        self.busy = True
        self.pending = list(routine.app_ids)
        self.routine_failures = []
        self.completed = 0
        self.routine_total = len(self.pending)
        GLib.idle_add(self._launch_next)

    def _launch_next(self):
        app_id = self.pending.pop(0)
        try:
            message = launch_app(self.apps, app_id)
        except Exception as exc:
            message = str(exc)
            self.routine_failures.append(message)
        self.completed += 1
        self.set_status(f"{self.completed}/{self.routine_total} · {message}")
        if self.pending:
            GLib.timeout_add(250, self._launch_next)
        else:
            self.busy = False
            summary = (f"{len(self.routine_failures)} launch request(s) failed: " + "; ".join(self.routine_failures)
                       if self.routine_failures else f"Sent {self.routine_total} launch requests. Apps may still be starting.")
            self.set_status(summary)
        return False

    def add_selection(self, app_id):
        if app_id not in self.selected_apps:
            self.selected_apps.append(app_id)
        self.selected_label.set_text(" → ".join(self.apps[i].get_display_name() for i in self.selected_apps))

    def clear_selection(self, *_):
        self.selected_apps.clear()
        self.selected_label.set_text("Use + beside an app to add it.")

    def save_routine(self, *_):
        name = self.routine_name.get_text().strip()
        aliases = tuple(a.strip() for a in self.routine_aliases.get_text().split(",") if a.strip())
        if self.config_error:
            self.set_status(self.config_error)
            return
        if not name or not self.selected_apps:
            self.set_status("Give the routine a name and add at least one app.")
            return
        routine = Routine(name, aliases, tuple(self.selected_apps))
        proposed = [*self.routines, routine]
        try:
            # Persist only if validation succeeds; existing routines are never silently replaced.
            save_routines(self.path, proposed)
        except (OSError, ValueError) as exc:
            self.set_status(str(exc))
            return
        self.routines = proposed
        self.catalog = build_catalog(self.apps, self.routines)
        self.voice_button.set_active(False)
        self.clear_selection()
        self.routine_name.set_text("")
        self.routine_aliases.set_text("")
        self.refresh_results()
        self.set_status(f"Saved {name}. Enable voice to load the updated command list.")

    def toggle_voice(self, button):
        if self.updating_switch:
            return
        self.voice_epoch += 1
        epoch = self.voice_epoch
        if self.listener:
            self.listener.stop()
            self.listener = None
        if not button.get_active():
            button.set_label("Enable voice")
            self.compact_status.set_text("Ready")
            self.set_status("Microphone off")
            return
        button.set_label("Disable voice")
        self.compact_status.set_text("Loading…")
        self.listener = VoiceListener(self.model, self.catalog.voice_phrases(),
                                      lambda event, text: GLib.idle_add(self.on_voice, epoch, event, text))
        self.listener.start()

    def on_voice(self, epoch, event, text):
        if epoch != self.voice_epoch:
            return False
        if event in {"loading", "ready", "timeout"}:
            self.set_status(text)
            self.compact_status.set_text("Mic on" if event != "loading" else "Loading…")
        elif event == "wake":
            self.expand()
            self.compact_status.set_text("Listening")
            self.set_status("Listening… Say an app name or a saved routine.")
        elif event == "command":
            self.search.set_text(text)
            if action := self.catalog.resolve(text):
                self.execute(action)
            else:
                self.set_status(f'Heard “{text}”. No unique exact match; nothing was launched.')
            self.compact_status.set_text("Mic on")
        elif event == "cancel":
            self.collapse()
        elif event == "error":
            self.set_status(text)
            self.compact_status.set_text("Voice error")
            self.updating_switch = True
            self.voice_button.set_active(False)
            self.voice_button.set_label("Enable voice")
            self.updating_switch = False
        return False

    def expand(self):
        self.expanded = True
        self.stack.set_visible_child_name("expanded")
        if self.is_island:
            LayerShell.set_keyboard_mode(self.window, LayerShell.KeyboardMode.EXCLUSIVE)
        self.window.present()
        self.search.grab_focus()

    def collapse(self):
        self.expanded = False
        self.stack.set_visible_child_name("compact")
        if self.is_island:
            LayerShell.set_keyboard_mode(self.window, LayerShell.KeyboardMode.ON_DEMAND)

    def on_key(self, _, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.collapse()
            return True
        if keyval in (Gdk.KEY_Up, Gdk.KEY_Down):
            row = self.results.get_selected_row()
            index = row.get_index() if row else -1
            target = index + (1 if keyval == Gdk.KEY_Down else -1)
            if target >= 0 and (next_row := self.results.get_row_at_index(target)):
                self.results.select_row(next_row)
            return True
        return False

    def on_close(self, *_):
        self.voice_epoch += 1
        if self.listener:
            self.listener.stop()
        return False

    def _smoke_collapse(self):
        self.collapse()
        return False

    def _smoke_expand(self):
        self.expand()
        return False

    def _snapshot(self):
        if path := os.environ.get("ORBIT_SNAPSHOT_PATH"):
            try:
                child = self.window.get_child()
                snapshot = Gtk.Snapshot()
                Gtk.WidgetPaintable.new(child).snapshot(snapshot, child.get_width(), child.get_height())
                node = snapshot.to_node()
                texture = self.window.get_renderer().render_texture(node, None)
                texture.save_to_png(path)
            except Exception as exc:
                print(f"Widget snapshot unavailable: {exc}", file=sys.stderr)
        return False

    def _smoke_quit(self):
        print(f"Orbit UI smoke: apps={len(self.apps)} island={self.is_island} · microphone unopened")
        self.window.close()
        return False


def run(model: Path, window_mode: bool, smoke_test: bool) -> int:
    if not Gtk.init_check() or Gdk.Display.get_default() is None:
        raise RuntimeError("No graphical session available. Use --doctor or run from your desktop terminal.")
    return OrbitApp(model, window_mode, smoke_test).run([])
