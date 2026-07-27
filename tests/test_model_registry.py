import tempfile
import unittest
from pathlib import Path

from tools.model_registry import discover_models


class DiscoverModelsTest(unittest.TestCase):
    def test_discovers_direct_model_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            alpha = root / "Alpha"
            alpha.mkdir()
            (alpha / "voice.pth").touch()
            (alpha / "trained_voice.index").touch()
            (alpha / "added_voice.index").touch()

            empty = root / "Empty"
            empty.mkdir()
            (empty / "only.index").touch()

            entries = discover_models(root)

            self.assertEqual([entry.name for entry in entries], ["Alpha"])
            self.assertEqual(entries[0].model_path.name, "voice.pth")
            self.assertEqual(entries[0].index_path.name, "added_voice.index")

    def test_returns_model_without_optional_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model_dir = root / "NoIndex"
            model_dir.mkdir()
            (model_dir / "voice.pth").touch()

            entries = discover_models(root)

            self.assertEqual(len(entries), 1)
            self.assertIsNone(entries[0].index_path)


if __name__ == "__main__":
    unittest.main()
