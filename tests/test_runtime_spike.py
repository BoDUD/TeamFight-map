from __future__ import annotations

import json
import struct
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPIKE_MOD = REPO_ROOT / "mods" / "tfm2_lol_map_spike"
SPIKE_BG = SPIKE_MOD / "aseprite_resources" / "ingame" / "5v5" / "background_5v5.png"
SPIKE_DOC = REPO_ROOT / "docs" / "runtime_map_loading_spike.md"


class RuntimeSpikeTests(unittest.TestCase):
    def test_mod_metadata_is_parseable_and_identifies_spike(self) -> None:
        metadata = json.loads((SPIKE_MOD / "mod.mod_info").read_text(encoding="utf-8"))
        self.assertEqual("tfm2_lol_map_spike", metadata["mod_id"])
        self.assertEqual("TFM2 LOL Map Runtime Spike", metadata["name"])
        self.assertEqual("0.1.0", metadata["version"])
        self.assertIn({"mod_id": "base", "version": ">=0.4.0"}, metadata["dependencies"])

    def test_override_table_only_replaces_background_probe(self) -> None:
        overrides = json.loads((SPIKE_MOD / "mod.override_info").read_text(encoding="utf-8"))
        self.assertEqual(
            ["asset/base/aseprite_resources/ingame/5v5/background_5v5"],
            sorted(overrides),
        )
        entry = overrides["asset/base/aseprite_resources/ingame/5v5/background_5v5"]
        self.assertEqual("override", entry["type"])
        self.assertEqual(
            "asset/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/background_5v5",
            entry["remapping"],
        )
        self.assertNotIn("asset/base/setting/map_setting", overrides)

    def test_background_probe_matches_native_background_size(self) -> None:
        data = SPIKE_BG.read_bytes()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual((1280, 1280), (width, height))

    def test_spike_doc_tracks_required_runtime_questions(self) -> None:
        text = SPIKE_DOC.read_text(encoding="utf-8")
        for phrase in (
            "Can map visuals be replaced by asset override?",
            "Can collision, minion paths, and spawn points be replaced by data files?",
            "does ModExtension/DLL expose enough map API?",
            "asset/base/setting/map_setting",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
