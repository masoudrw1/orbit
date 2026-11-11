from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.build_deb import cached_asset, debian_version, extract_vosk, tree_hash


class PackageTests(unittest.TestCase):
    def test_alpha_version_sorts_before_final_debian_version(self):
        self.assertEqual(debian_version("0.1.0a2"), "0.1.0~alpha2-1")
        with self.assertRaises(ValueError):
            debian_version("0.1.0\nDepends: other")

    def test_model_digest_detects_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / "model"
            file.write_bytes(b"original")
            before = tree_hash(root)
            file.write_bytes(b"changed")
            self.assertNotEqual(tree_hash(root), before)

    def test_modified_cached_download_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "asset").write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "changed"):
                cached_asset({"filename": "asset", "sha256": "0" * 64}, root, False)

    def test_wheel_cannot_escape_package_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "test.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("vosk/../../escape", "bad")
            with self.assertRaises(ValueError):
                extract_vosk(wheel, root / "vendor")
            self.assertFalse((root / "escape").exists())


if __name__ == "__main__":
    unittest.main()
