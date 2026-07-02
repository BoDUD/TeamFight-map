from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools import inventory_visual_override_surfaces as inventory


REPO_ROOT = Path(__file__).resolve().parents[1]
MOD_ROOT = REPO_ROOT / "mods" / "tfm2_lol_map_spike"
OVERRIDE_INFO = MOD_ROOT / "mod.override_info"


def write_png(path: Path, size: tuple[int, int] = (8, 8), color: tuple[int, int, int, int] = (20, 120, 60, 255)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", size, color)
    image.save(path)


class VisualMapDetailAssetInventoryTests(unittest.TestCase):
    def test_inventory_writes_json_only_and_keeps_runtime_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scan_root = root / "native_layer_extracts"
            output_dir = root / "evidence"
            write_png(scan_root / "wall_5v5.png", (32, 32))
            write_png(scan_root / "wall_5v5_front.png", (32, 32))
            write_png(scan_root / "bush_5v5.png", (32, 32))
            write_png(scan_root / "monsters" / "serpen_idle.png", (16, 16))

            summary = inventory.write_inventory([scan_root], output_dir)
            manifest_path = output_dir / inventory.OUTPUT_FILENAME
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(4, summary["image_candidate_count"])
            self.assertFalse((output_dir / "mod.override_info").exists())
            self.assertFalse((output_dir / "map_setting.map_setting").exists())
            self.assertFalse((output_dir / "minimap_5v5_bg.png").exists())
            self.assertFalse(manifest["default_runtime_package_changed"])
            self.assertFalse(manifest["map_setting_override_installed"])
            self.assertFalse(manifest["minimap_default_enabled"])
            self.assertFalse(manifest["gameplay_data_modified"])
            self.assertFalse(manifest["runtime_mutation_allowed"])
            self.assertFalse(manifest["packed4_mutation_allowed"])
            self.assertFalse(manifest["map_editing_allowed"])

            wall = next(item for item in manifest["surface_matrix"] if item["asset_candidate"] == "wall_5v5")
            self.assertTrue(wall["native_reference_found"])
            self.assertEqual("medium", wall["risk"])

    def test_repository_runtime_package_still_background_only(self) -> None:
        table = json.loads(OVERRIDE_INFO.read_text(encoding="utf-8"))
        self.assertEqual(
            {"asset/base/aseprite_resources/ingame/5v5/background_5v5"},
            set(table),
        )
        serialized = json.dumps(table, sort_keys=True)
        self.assertNotIn("minimap_5v5_bg", serialized)
        self.assertNotIn("asset/base/setting/map_setting", serialized)
        self.assertFalse((MOD_ROOT / "setting" / "map_setting.map_setting").exists())

    def test_rejects_repository_internal_output_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            scan_root = Path(temp_dir) / "native_layer_extracts"
            write_png(scan_root / "wall_5v5.png")
            output_dir = REPO_ROOT / ".tmp_visual_inventory_should_not_exist"

            with self.assertRaises(SystemExit) as raised:
                inventory.write_inventory([scan_root], output_dir)

            self.assertIn("inside the repository", str(raised.exception))
            self.assertFalse(output_dir.exists())

    def test_rejects_output_under_mods_tree_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scan_root = root / "native_layer_extracts"
            output_dir = root / "game" / "mods" / "tfm2_lol_map_spike" / "inventory"
            write_png(scan_root / "wall_5v5.png")

            with self.assertRaises(SystemExit) as raised:
                inventory.write_inventory([scan_root], output_dir)

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertFalse(output_dir.exists())

    def test_rejects_runtime_mods_scan_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scan_root = root / "game" / "mods" / "tfm2_lol_map_spike"
            output_dir = root / "evidence"
            write_png(scan_root / "wall_5v5.png")

            with self.assertRaises(SystemExit) as raised:
                inventory.write_inventory([scan_root], output_dir)

            self.assertIn("runtime mods tree", str(raised.exception))
            self.assertFalse(output_dir.exists())

    def test_rejects_output_hardlink_alias_to_scanned_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scan_root = root / "native_layer_extracts"
            output_dir = root / "evidence"
            source = scan_root / "wall_5v5.png"
            write_png(source)
            output_dir.mkdir()
            output_path = output_dir / inventory.OUTPUT_FILENAME
            try:
                os.link(source, output_path)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")
            before = source.read_bytes()

            with self.assertRaises(SystemExit) as raised:
                inventory.write_inventory([scan_root], output_dir)

            self.assertIn("Refusing to overwrite", str(raised.exception))
            self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
