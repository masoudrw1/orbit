# Install and activate Orbit alpha 2

The first package targets Pop!_OS 24.04 on amd64, with COSMIC/Wayland for the
native island. The Ubuntu 24.04 package dependency set is used. Native GNOME island
support remains a future phase; its normal-window fallback is not a tested GNOME release.

## Install

Close the old development prototype first. In the directory containing the installer:

```bash
sudo apt install './orbit-launcher_0.1.0~alpha2-1_amd64.deb'
```

APT installs missing standard dependencies. The offline model is already bundled.
Orbit appears in the application menu. Installation itself does not activate it.

## Activate

1. Open Orbit from the app menu.
2. Choose whether **Start Orbit when I sign in** should be enabled.
3. Click **Activate Hey Orbit** and wait for the model to load.
4. Orbit hides. Say **Hey Orbit**, pause, then a command such as **open browser**
   (when Firefox is installed) or the name of a saved routine.
5. Escape or **−** hides the island again. A completed voice command also hides it
   after a short delay, unless you start using the keyboard.

Open Orbit from the app menu at any time to return to its controls. Starting it
again reuses the existing instance. The microphone uses the default desktop input.
Input selection and broader accent/noise measurements remain later work.

## Stop and recover

- **Deactivate Hey Orbit** stops the current listener and disables saved activation
  and login startup. Typing/search remain available while the UI is open.
- **×** or `orbit --quit` exits for this session. Saved activation is retained;
  if login startup is enabled, it resumes after the next sign-in.
- If microphone or model initialization fails, Orbit shows its controls and error.
  Deactivate and activate again after fixing the input/device problem.
- `orbit --doctor` reports runtime and activation prerequisites without recording.
- `orbit --window` requests the normal-window presentation adapter on a new instance.
  Quit the existing instance first if changing presentation mode.

Settings are per user, normally in `~/.config/orbit/settings.json` and
`~/.config/orbit/routines.json`. Login startup is a standard XDG entry at
`~/.config/autostart/io.github.masoudrw1.Orbit.desktop`. A fresh background launch
does nothing if saved activation is off. It does not run as root or as a boot daemon.
Model inference is local; Orbit does not upload or save microphone audio.

## Remove

Quit Orbit first, then:

```bash
sudo apt remove orbit-launcher
```

User routines/settings are preserved. A remaining login entry has `TryExec`, so
it is skipped once the installed launcher is absent. Deactivate before removal to
remove the login entry as well. No package hook scans or deletes home directories.

## Current validation limit

The installer is an alpha. Extraction, system-Python runtime, Ubuntu dependency
resolution, synthetic audio, and isolated GTK lifecycle tests were checked.
An actual privileged installation, real login/logout, real microphone wake testing
of the installed version, and clean-machine testing must still be completed.
