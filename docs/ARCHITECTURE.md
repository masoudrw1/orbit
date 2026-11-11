# Architecture

The primary target is COSMIC on Wayland. Future Ubuntu/GNOME support is a product
requirement, not an existing compatibility claim.

```text
typed text ─────────────────────┐
                               v
microphone → speech → wake gate → command catalog → desktop action
                                      ^                  |
                                      |                  v
                                saved routines       UI status
```

- `core.py`: pure Python normalization, exact command resolution, text search,
  and the time-limited voice activation state. No GUI or OS imports.
- `config.py`: validated routine data and atomic user configuration writes.
- `desktop.py`: Linux desktop-file discovery and Gio launch requests.
- `voice.py`: optional, background-thread speech adapter; emits events and does
  not import GTK. The UI delivers events to GTK's main thread with GLib.
- `ui.py`: presentation and user interactions. It asks the other modules for work.
- `style.css`: the initial visual design.

## Presentation backends

The initial GTK UI uses Layer Shell only when its library, typelib, and compositor
support are available. The library is preloaded before GTK opens Wayland.
The collapsed surface releases exclusive keyboard focus; expansion requests
keyboard focus for the search field. This requires testing with other applications,
fullscreen windows, multiple monitors, display scaling, and the COSMIC panel.

GNOME/Wayland does not support this Layer Shell route. Plan a thin GNOME Shell
extension communicating with a desktop-independent Orbit service, or retain a
clearly identified ordinary-window mode. A native GNOME island will require
some GJS/JavaScript and version-specific compatibility work. The present UI is
not yet a separate service; that boundary must be extracted before the extension.
Do not rewrite voice recognition or command matching in the extension.

## Speech decision for the alpha

Use Vosk's small English streaming model for the first integration experiment.
This replaces the earlier tentative openWakeWord/Whisper combination for the
alpha, not as a proven final engine choice. It keeps one inference engine and
provides an Apache-2.0 English model. The wake phrase is ordinary constrained
speech recognition, so it is not expected to match a tuned dedicated detector
without measurement. The event boundary allows replacing either component later.

Evaluate real accents, noisy rooms, unrelated conversations, idle CPU, memory,
and command latency. Unsupported/ambiguous words must not silently launch an app.
Offline behavior requires dependencies and the speech model to be installed first.

## Actions

The alpha supports desktop app launch requests grouped in routines. It never
evaluates recognized or typed text as shell code. Future action types should be
explicit objects: app plus project directory, URL, user service, and system
service. PostgreSQL startup needs service-specific authorization and readiness
handling. Opening its management GUI is a different app action.

Do not equate a launch request being accepted with app readiness. Do not hide
individual routine failures behind a successful overall message.
