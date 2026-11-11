import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from orbit.activation import Preferences, _atomic_write, apply_preferences, desktop_entry, read_preferences


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.settings = self.root / "orbit/settings.json"
        self.startup = self.root / "autostart/orbit.desktop"
        self.launcher = self.root / "Orbit App/run.sh"
        self.launcher.parent.mkdir()
        self.launcher.write_text("#!/bin/sh\nexit 0\n")
        self.launcher.chmod(0o755)

    def apply(self, preferences):
        apply_preferences(preferences, self.launcher, self.settings, self.startup)

    def test_install_defaults_do_not_activate_or_create_files(self):
        self.assertEqual(read_preferences(self.settings), Preferences())
        self.assertFalse(self.settings.exists())
        self.assertFalse(self.startup.exists())

    def test_activation_survives_restart_and_creates_login_entry(self):
        self.apply(Preferences(True, True))
        self.assertEqual(read_preferences(self.settings), Preferences(True, True))
        content = self.startup.read_text()
        self.assertIn(f'Exec="{self.launcher}" --background', content)
        self.assertIn(f"TryExec={self.launcher}", content)

    def test_deactivation_removes_only_orbits_login_entry(self):
        self.apply(Preferences(True, True))
        unrelated = self.startup.with_name("another-app.desktop")
        unrelated.write_text("keep this")
        self.apply(Preferences())
        self.assertFalse(self.startup.exists())
        self.assertEqual(unrelated.read_text(), "keep this")
        self.assertEqual(read_preferences(self.settings), Preferences())

    def test_activation_can_be_session_only(self):
        self.apply(Preferences(True, False))
        self.assertEqual(read_preferences(self.settings), Preferences(True, False))
        self.assertFalse(self.startup.exists())

    def test_failed_settings_write_rolls_back_login_entry_and_settings(self):
        self.apply(Preferences(True, True))
        original = self.startup.read_bytes(), self.settings.read_bytes()
        def write(path, content):
            if path == self.settings:
                raise OSError("simulated settings disk failure")
            _atomic_write(path, content)
        with patch("orbit.activation._atomic_write", side_effect=write):
            with self.assertRaises(OSError):
                self.apply(Preferences())
        self.assertEqual((self.startup.read_bytes(), self.settings.read_bytes()), original)

    def test_invalid_preferences_never_become_activation(self):
        self.settings.parent.mkdir()
        self.settings.write_text(json.dumps({"version": 1, "enabled": "false", "start_at_login": False}))
        with self.assertRaises(ValueError):
            read_preferences(self.settings)
        with self.assertRaises(ValueError):
            self.apply(Preferences(False, True))
        self.assertFalse(self.startup.exists())

    def test_startup_requires_an_executable_launcher(self):
        self.launcher.chmod(0o644)
        with self.assertRaises(ValueError):
            self.apply(Preferences(True, True))
        self.assertFalse(self.settings.exists())
        self.assertFalse(self.startup.exists())

    def test_desktop_exec_escapes_field_codes_and_rejects_line_injection(self):
        entry = desktop_entry(self.root / 'name%f"$x/run.sh')
        self.assertIn("name%%f", entry)
        self.assertIn('\\"', entry)
        self.assertIn("\\$", entry)
        with self.assertRaises(ValueError):
            desktop_entry(self.root / "bad\nExec=other")


if __name__ == "__main__":
    unittest.main()
