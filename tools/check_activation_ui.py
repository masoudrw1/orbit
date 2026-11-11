#!/usr/bin/env python3
"""Real GTK/Wayland activation test with a fake microphone adapter.

Run from the source checkout with native runtime paths set by run.sh (see phase
guide). A separate D-Bus session is required to avoid controlling the user's
running Orbit. No microphone is opened, and no desktop app is launched.
"""

import os
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["activation", "resume", "disabled"], default="activation")
    parser.add_argument("--package-root", type=Path, help="Test an extracted installer instead of the source UI")
    args = parser.parse_args()
    package_root = args.package_root.resolve() if args.package_root else None
    sys.path.insert(0, str(package_root / "opt/orbit/app" if package_root else ROOT))
    child_command = [str(package_root / "usr/bin/orbit")] if package_root else ["bash", str(ROOT / "run.sh")]
    launcher = package_root / "opt/orbit/bin/orbit" if package_root else ROOT / "run.sh"
    if os.environ.get("ORBIT_TEST_ISOLATED_BUS") != "1":
        raise SystemExit("Run this helper through dbus-run-session with ORBIT_TEST_ISOLATED_BUS=1.")
    with tempfile.TemporaryDirectory(prefix="orbit-activation-") as temporary:
        root = Path(temporary)
        os.environ.update({
            "ORBIT_SETTINGS_PATH": str(root / "settings.json"),
            "ORBIT_AUTOSTART_DIR": str(root / "autostart"),
            "ORBIT_CONFIG_PATH": str(root / "routines.json"),
            "ORBIT_LAUNCHER": str(launcher),
        })
        import orbit.ui as ui
        from gi.repository import GLib
        from orbit.activation import Preferences, apply_preferences, read_preferences, autostart_path
        failures, checks, listeners = [], [], []

        class FakeVoice:
            def __init__(self, model, phrases, emit):
                self.emit, self.stopped = emit, False
                listeners.append(self)
            def start(self):
                self.emit("ready", "Test microphone ready (fake adapter)")
            def stop(self):
                self.stopped = True

        ui.VoiceListener = FakeVoice
        if args.mode == "resume":
            apply_preferences(Preferences(True, True), launcher)
        app = ui.OrbitApp(root / "unused-model", False, False)
        if args.mode == "disabled":
            app.run(["orbit", "--background"])
            assert app.window is None and not listeners
            print("Deactivated login startup exits without a window or voice listener.")
            return

        def guarded(callback):
            def run():
                try:
                    callback()
                except Exception as exc:
                    failures.append(f"{callback.__name__}: {exc!r}")
                    app.quit_orbit()
                return False
            return run

        def activate():
            app.voice_button.set_active(True)
            assert read_preferences().enabled
            assert autostart_path().exists()
            GLib.timeout_add(150, guarded(hidden))

        def hidden():
            assert not app.window.get_visible(), "activation did not hide the island"
            checks.append("activation hides the island")
            listeners[-1].emit("wake", "")
            GLib.timeout_add(150, guarded(woken))

        def woken():
            assert app.window.get_visible() and app.expanded
            checks.append("wake event reveals the island")
            app.collapse()
            assert not app.window.get_visible()
            # A second process must activate this UI, not construct another listener.
            process = subprocess.Popen(child_command, env=os.environ.copy(),
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            started = time.monotonic()
            def await_remote():
                try:
                    if process.poll() is None:
                        if time.monotonic() - started > 8:
                            process.kill()
                            process.communicate()
                            raise RuntimeError("second launch did not return")
                        return True
                    stdout, stderr = process.communicate()
                    assert process.returncode == 0, stderr
                    GLib.timeout_add(100, guarded(reopened))
                except Exception as exc:
                    failures.append(f"second launch: {exc!r}")
                    app.quit_orbit()
                return False
            GLib.timeout_add(50, await_remote)

        def reopened():
            assert app.window.get_visible()
            assert len(listeners) == 1, "second launch constructed a second voice listener"
            checks.append("second launch reopens the same instance")
            listeners[-1].emit("error", "Test microphone error")
            GLib.timeout_add(150, guarded(recover))

        def recover():
            assert app.window.get_visible()
            assert "Test microphone error" in app.status.get_text()
            checks.append("voice errors reveal recovery controls")
            with patch.object(ui, "apply_preferences", side_effect=OSError("test disk failure")):
                app.voice_button.set_active(False)
            assert listeners[-1].stopped, "disk failure prevented microphone stop"
            assert read_preferences().enabled, "failed save should retain the previous preference"
            assert "Microphone stopped" in app.status.get_text()
            checks.append("deactivation stops the microphone even if saving fails")
            app.voice_button.set_active(False)
            assert not read_preferences().enabled
            assert not autostart_path().exists()
            assert listeners[-1].stopped
            checks.append("deactivation stops the listener and removes login startup")
            app.quit_orbit()

        def resumed():
            assert read_preferences().enabled and len(listeners) == 1
            assert not app.window.get_visible()
            checks.append("saved activation resumes hidden")
            listeners[-1].emit("wake", "")
            GLib.timeout_add(150, guarded(resume_woken))

        def resume_woken():
            assert app.window.get_visible()
            checks.append("resumed listener reveals the island on wake")
            app.quit_orbit()

        GLib.timeout_add(250, guarded(resumed if args.mode == "resume" else activate))
        GLib.timeout_add_seconds(15, guarded(lambda: (_ for _ in ()).throw(RuntimeError("UI check timed out"))))
        app.run(["orbit", "--background"] if args.mode == "resume" else ["orbit"])
        expected = 2 if args.mode == "resume" else 6
        if failures or len(checks) != expected:
            raise SystemExit(f"Activation UI check failed: {failures}; completed checks: {checks}")
        print("Activation UI checks passed:\n- " + "\n- ".join(checks))


if __name__ == "__main__":
    main()
