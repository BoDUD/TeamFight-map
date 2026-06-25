from __future__ import annotations

import json
import tempfile
import struct
import unittest
from unittest import mock
from pathlib import Path

from tools import install_runtime_spike_mod


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

    def test_map_setting_equivalent_staging_only_mutates_installed_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game_root = Path(temp_dir) / "game"
            (game_root / "mods").mkdir(parents=True)
            (game_root / "mod-sdk").mkdir()
            (game_root / "TeamfightManager2.exe").write_bytes(b"")
            (game_root / "mod-sdk" / "base_version.txt").write_text("0.4.4\n", encoding="utf-8")
            source = Path(temp_dir) / "map_setting"
            source.write_bytes(b"byte-identical-map-setting-probe")

            installed = install_runtime_spike_mod.copy_mod(game_root, clean=True)
            manifest_path = install_runtime_spike_mod.stage_map_setting_equivalent(game_root, installed, source)

            target = installed / "setting" / "map_setting.map_setting"
            self.assertEqual(source.read_bytes(), target.read_bytes())
            self.assertTrue(install_runtime_spike_mod.files_are_byte_equal(source, target))

            installed_overrides = json.loads((installed / "mod.override_info").read_text(encoding="utf-8"))
            self.assertIn("asset/base/setting/map_setting", installed_overrides)
            self.assertEqual(
                {
                    "remapping": "asset/tfm2_lol_map_spike/setting/map_setting",
                    "type": "override",
                },
                installed_overrides["asset/base/setting/map_setting"],
            )

            repo_overrides = json.loads((SPIKE_MOD / "mod.override_info").read_text(encoding="utf-8"))
            self.assertNotIn("asset/base/setting/map_setting", repo_overrides)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(str(source.resolve()), manifest["source_path"])
            self.assertEqual(str(target), manifest["target_path"])
            self.assertEqual(manifest["source_size"], manifest["target_size"])
            self.assertEqual(manifest["source_sha256"], manifest["target_sha256"])
            self.assertEqual(0, manifest["game_exe_size"])
            self.assertEqual(install_runtime_spike_mod.sha256_file(game_root / "TeamfightManager2.exe"), manifest["game_exe_sha256"])
            self.assertTrue(manifest["byte_equal"])
            self.assertFalse(manifest["committed_to_repository"])

    def test_clean_install_refuses_to_delete_repository_source_mod(self) -> None:
        with mock.patch.object(install_runtime_spike_mod.shutil, "rmtree") as mocked_rmtree:
            with self.assertRaises(SystemExit) as raised:
                install_runtime_spike_mod.copy_mod(REPO_ROOT, clean=True)

            self.assertIn("repository source mod package", str(raised.exception))
            mocked_rmtree.assert_not_called()


if __name__ == "__main__":
    unittest.main()
