from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import audit_runtime_node_anchor_api, install_runtime_anchor_probe


ROOT = Path(__file__).resolve().parents[1]
ANCHOR_MOD = ROOT / "mods" / "tfm2_lol_anchor_probe"


class RuntimeAnchorProbeTests(unittest.TestCase):
    def make_game_root(self, temp_dir: str) -> Path:
        game_root = Path(temp_dir) / "game"
        (game_root / "mods").mkdir(parents=True)
        (game_root / "config" / "game").mkdir(parents=True)
        (game_root / "TeamfightManager2.exe").write_bytes(b"")
        (game_root / "config" / "game" / "mods.json").write_text(
            json.dumps(
                {
                    "enabled_mods": ["other_mod"],
                    "known_workshop_mods": [],
                    "accepted_code_mod_warnings": [],
                    "accepted_save_mod_mismatch_warnings": [],
                }
            ),
            encoding="utf-8",
        )
        return game_root

    def test_anchor_probe_source_has_no_asset_overrides(self) -> None:
        metadata = json.loads((ANCHOR_MOD / "mod.mod_info").read_text(encoding="utf-8"))
        self.assertEqual("tfm2_lol_anchor_probe", metadata["mod_id"])
        self.assertFalse((ANCHOR_MOD / "mod.override_info").exists())
        self.assertFalse((ANCHOR_MOD / "setting" / "map_setting.map_setting").exists())
        self.assertFalse(
            (ANCHOR_MOD / "aseprite_resources" / "ingame" / "5v5" / "background_5v5.png").exists()
        )

    def test_install_anchor_probe_copies_only_metadata_and_dll(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game_root = self.make_game_root(temp_dir)
            dll = Path(temp_dir) / "runtime_node_anchor_probe.dll"
            dll.write_bytes(b"fake dll")
            evidence_dir = Path(temp_dir) / "evidence"

            manifest = install_runtime_anchor_probe.install_anchor_probe(
                game_root,
                dll,
                evidence_dir,
                clean=False,
                enable_exclusive=True,
            )

            installed = game_root / "mods" / "tfm2_lol_anchor_probe"
            self.assertTrue((installed / "tfm2_lol_anchor_probe.dll").is_file())
            self.assertTrue((installed / "probe_evidence_dir.txt").is_file())
            self.assertFalse((installed / "mod.override_info").exists())
            self.assertFalse((installed / "setting" / "map_setting.map_setting").exists())
            self.assertFalse((installed / "aseprite_resources" / "ingame" / "5v5" / "background_5v5.png").exists())
            self.assertFalse(manifest["map_setting_override_installed"])
            self.assertFalse(manifest["asset_overrides_installed"])
            self.assertFalse(manifest["mod_override_info_present"])
            self.assertEqual("unproven", manifest["map_setting_node_world_transform"])

            written_manifest = json.loads((evidence_dir / "probe_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["probe_dll_sha256"], written_manifest["probe_dll_sha256"])
            config = json.loads((game_root / "config" / "game" / "mods.json").read_text(encoding="utf-8"))
            self.assertEqual(["tfm2_lol_anchor_probe"], config["enabled_mods"])
            self.assertIn("tfm2_lol_anchor_probe", config["accepted_code_mod_warnings"])

    def test_install_anchor_probe_rejects_existing_override_artifacts(self) -> None:
        forbidden_relatives = [
            Path("mod.override_info"),
            Path("setting") / "map_setting.map_setting",
            Path("aseprite_resources") / "ingame" / "5v5" / "background_5v5.png",
        ]
        for relative in forbidden_relatives:
            with self.subTest(relative=relative):
                with tempfile.TemporaryDirectory() as temp_dir:
                    game_root = self.make_game_root(temp_dir)
                    installed = game_root / "mods" / "tfm2_lol_anchor_probe"
                    installed.mkdir()
                    forbidden = installed / relative
                    forbidden.parent.mkdir(parents=True, exist_ok=True)
                    forbidden.write_text("forbidden", encoding="utf-8")
                    dll = Path(temp_dir) / "runtime_node_anchor_probe.dll"
                    dll.write_bytes(b"fake dll")

                    with self.assertRaises(SystemExit) as raised:
                        install_runtime_anchor_probe.install_anchor_probe(
                            game_root,
                            dll,
                            Path(temp_dir) / "evidence",
                            clean=False,
                            enable_exclusive=False,
                        )

                    self.assertIn("forbidden override artifacts", str(raised.exception))
                    self.assertEqual("forbidden", forbidden.read_text(encoding="utf-8"))

    def test_install_anchor_probe_rejects_repository_evidence_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game_root = self.make_game_root(temp_dir)
            dll = Path(temp_dir) / "runtime_node_anchor_probe.dll"
            dll.write_bytes(b"fake dll")

            with self.assertRaises(SystemExit) as raised:
                install_runtime_anchor_probe.install_anchor_probe(
                    game_root,
                    dll,
                    ROOT / "evidence",
                    clean=False,
                    enable_exclusive=False,
                )

            self.assertIn("inside the repository", str(raised.exception))
            self.assertFalse((game_root / "mods" / "tfm2_lol_anchor_probe").exists())

    def test_install_anchor_probe_rejects_repository_dll_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game_root = self.make_game_root(temp_dir)
            with self.assertRaises(SystemExit) as raised:
                install_runtime_anchor_probe.install_anchor_probe(
                    game_root,
                    ROOT / "native" / "runtime_node_anchor_probe" / "runtime_node_anchor_probe.dll",
                    Path(temp_dir) / "evidence",
                    clean=False,
                    enable_exclusive=False,
                )

            self.assertIn("outside the repository", str(raised.exception))
            self.assertFalse((game_root / "mods" / "tfm2_lol_anchor_probe").exists())

    def test_delete_safety_refuses_repository_source_target(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            install_runtime_anchor_probe.ensure_delete_target_is_safe(
                ROOT,
                ROOT / "mods" / "tfm2_lol_anchor_probe",
            )
        self.assertIn("repository source anchor probe package", str(raised.exception))

    def test_audit_runtime_node_anchor_api_on_synthetic_sdk(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sdk = Path(temp_dir) / "sdk"
            (sdk / "template" / "src").mkdir(parents=True)
            (sdk / "template" / "src" / "lib.rs").write_text(
                """
use mod_api::*;
impl ModExtension for Probe {
    fn post_update(&self, scene: &mut Scene, ui: &mut GameUI, assets: &mut Assets, dt: f32) {}
}
""",
                encoding="utf-8",
            )

            audit = audit_runtime_node_anchor_api.audit_sdk(sdk, [])
            rows = {row["api_surface"]: row for row in audit["surfaces"]}

            self.assertTrue(rows["ModExtension::post_update"]["public_in_checked_sources"])
            self.assertTrue(rows["Scene"]["public_in_checked_sources"])
            self.assertFalse(rows["world_to_screen / screen_to_world"]["public_in_checked_sources"])
            self.assertEqual("unproven", audit["result"]["map_setting_node_world_transform"])
            self.assertEqual("blocked", audit["result"]["candidate_369_370"])

    def test_audit_output_rejects_sdk_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sdk = Path(temp_dir) / "sdk"
            source = sdk / "template" / "src" / "lib.rs"
            source.parent.mkdir(parents=True)
            source.write_text("sdk source", encoding="utf-8")

            with self.assertRaises(SystemExit) as raised:
                audit_runtime_node_anchor_api.ensure_audit_output_is_safe(source, sdk, [])

            self.assertIn("checked SDK directory", str(raised.exception))
            self.assertEqual("sdk source", source.read_text(encoding="utf-8"))

    def test_audit_output_rejects_extra_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sdk = Path(temp_dir) / "sdk"
            sdk.mkdir()
            extra = Path(temp_dir) / "adjacent" / "lib.rs"
            extra.parent.mkdir()
            extra.write_text("extra source", encoding="utf-8")

            with self.assertRaises(SystemExit) as raised:
                audit_runtime_node_anchor_api.ensure_audit_output_is_safe(extra, sdk, [extra])

            self.assertIn("checked source file", str(raised.exception))
            self.assertEqual("extra source", extra.read_text(encoding="utf-8"))

    def test_audit_output_rejects_hardlink_alias_of_extra_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sdk = Path(temp_dir) / "sdk"
            sdk.mkdir()
            extra = Path(temp_dir) / "adjacent" / "lib.rs"
            alias = Path(temp_dir) / "evidence" / "audit.json"
            extra.parent.mkdir()
            alias.parent.mkdir()
            extra.write_text("extra source", encoding="utf-8")
            os.link(extra, alias)

            with self.assertRaises(SystemExit) as raised:
                audit_runtime_node_anchor_api.ensure_audit_output_is_safe(alias, sdk, [extra])

            self.assertIn("checked source file", str(raised.exception))
            self.assertEqual("extra source", extra.read_text(encoding="utf-8"))

    def test_audit_output_rejects_hardlink_alias_of_sdk_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sdk = Path(temp_dir) / "sdk"
            source = sdk / "template" / "src" / "lib.rs"
            alias = Path(temp_dir) / "evidence" / "audit.json"
            source.parent.mkdir(parents=True)
            alias.parent.mkdir()
            source.write_text("sdk source", encoding="utf-8")
            os.link(source, alias)

            with self.assertRaises(SystemExit) as raised:
                audit_runtime_node_anchor_api.ensure_audit_output_is_safe(alias, sdk, [])

            self.assertIn("checked source file", str(raised.exception))
            self.assertEqual("sdk source", source.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
