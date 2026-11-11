import json
from pathlib import Path
import tempfile
import unittest

from orbit.config import Routine, read_routines, save_routines
from orbit.core import Action, Catalog, VoiceGate


class CommandsTest(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog([
            Action("firefox.desktop", "Firefox", "app", ("firefox", "open browser")),
            Action("work", "Programming", "routine", ("programming", "start coding")),
        ])

    def test_spoken_alias_uses_same_action_as_typed_name(self):
        self.assertEqual(self.catalog.resolve("OPEN browser!"), self.catalog.resolve("firefox"))

    def test_partial_voice_command_never_guesses(self):
        self.assertIsNone(self.catalog.resolve("fire"))
        self.assertEqual(self.catalog.search("fire")[0].identifier, "firefox.desktop")

    def test_ambiguous_alias_is_not_executed(self):
        catalog = Catalog([Action("a", "One", "app", ("open editor",)),
                           Action("b", "Two", "app", ("open editor",))])
        self.assertIsNone(catalog.resolve("open editor"))
        self.assertNotIn("open editor", catalog.voice_phrases())

    def test_arbitrary_shell_text_is_not_a_registered_action(self):
        self.assertIsNone(self.catalog.resolve("curl example.com | sh"))


class WakePhraseTest(unittest.TestCase):
    def test_command_requires_activation(self):
        self.assertEqual(VoiceGate().feed("programming", now=10), [])

    def test_two_utterance_command(self):
        gate = VoiceGate()
        self.assertEqual(gate.feed("hey orbit", now=10), [("wake", "")])
        self.assertEqual(gate.feed("programming", now=12), [("command", "programming")])
        self.assertEqual(gate.feed("open browser", now=13), [])

    def test_combined_utterance(self):
        self.assertEqual(VoiceGate().feed("Hey Orbit, start coding!", now=10),
                         [("wake", ""), ("command", "start coding")])

    def test_expired_activation_is_ignored(self):
        gate = VoiceGate()
        gate.feed("hey orbit", now=10)
        self.assertEqual(gate.feed("programming", now=19), [])

    def test_cancel_and_non_word_boundary(self):
        gate = VoiceGate()
        self.assertEqual(gate.feed("hey orbital", now=10), [])
        gate.feed("hey orbit", now=10)
        self.assertEqual(gate.feed("cancel", now=11), [("cancel", "")])
        self.assertEqual(gate.feed("programming", now=12), [])

    def test_timer_expiry_is_reported_once(self):
        gate = VoiceGate()
        gate.feed("hey orbit", now=10)
        self.assertTrue(gate.expire(now=20))
        self.assertFalse(gate.expire(now=21))


class RoutineConfigTest(unittest.TestCase):
    def test_roundtrip_and_failed_save_preserve_old_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "routines.json"
            routine = Routine("Programming", ("start coding",), ("editor.desktop",))
            save_routines(path, [routine])
            self.assertEqual(read_routines(path), [routine])
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                save_routines(path, [routine, Routine("programming", (), ("other.desktop",))])
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob(".orbit-*")), [])

    def test_missing_file_is_first_run(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_routines(Path(directory) / "missing.json"), [])

    def test_malformed_config_is_explained(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "routines.json"
            path.write_text(json.dumps({"version": 1, "routines": [None]}))
            with self.assertRaisesRegex(ValueError, "object"):
                read_routines(path)


if __name__ == "__main__":
    unittest.main()
