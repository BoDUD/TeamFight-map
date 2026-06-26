from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import install_runtime_mutation_probe, install_runtime_spike_mod


class RuntimeMutationProbeTests(unittest.TestCase):
    def make_game_root(self, temp_dir: str) -> Path:
        game_root = Path(temp_dir) / "game"
        (game_root / "mods").mkdir(parents=True)
        (game_root / "mod-sdk").mkdir()
        (game_root / "TeamfightManager2.exe").write_bytes(b"")
        (game_root / "mod-sdk" / "base_version.txt").write_text("0.4.4\n", encoding="utf-8")
        return game_root

    def write_source(self, root: Path, name: str, data: bytes) -> Path:
        source = root / "sources" / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(data)
        return source

    def write_q2e_pair(self, root: Path) -> tuple[Path, Path]:
        size = max(install_runtime_mutation_probe.EXPECTED_MUTATION_OFFSETS) + 1
        original = bytearray(size)
        for offset in install_runtime_mutation_probe.EXPECTED_MUTATION_OFFSETS:
            original[offset] = 1
        mutated = bytearray(original)
        for offset in install_runtime_mutation_probe.EXPECTED_MUTATION_OFFSETS:
            mutated[offset] = 0
        original_path = self.write_source(root, "original.map_setting", bytes(original))
        mutated_path = self.write_source(root, "map_setting.q2e.mutated.map_setting", bytes(mutated))
        return original_path, mutated_path

    def test_stage_a1_original_map_setting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_root = self.make_game_root(temp_dir)
            data = b"baseline"
            source = self.write_source(root, "map_setting.map_setting", data)
            expected_sha = install_runtime_spike_mod.sha256_file(source)
            old_baseline = install_runtime_mutation_probe.BASELINE_SHA256
            install_runtime_mutation_probe.BASELINE_SHA256 = expected_sha
            try:
                manifest = install_runtime_mutation_probe.stage_runtime_mutation_probe(
                    game_root=game_root,
                    mode="A1",
                    map_setting_source=source,
                    evidence_dir=root / "evidence",
                    clean=True,
                    enable_exclusive=True,
                )
            finally:
                install_runtime_mutation_probe.BASELINE_SHA256 = old_baseline

            target = game_root / "mods" / "tfm2_lol_map_spike" / "setting" / "map_setting.map_setting"
            self.assertEqual(data, target.read_bytes())
            overrides = json.loads((game_root / "mods" / "tfm2_lol_map_spike" / "mod.override_info").read_text())
            self.assertEqual(
                [
                    "asset/base/aseprite_resources/ingame/5v5/background_5v5",
                    "asset/base/setting/map_setting",
                ],
                sorted(overrides),
            )
            self.assertEqual("A1", manifest["mode"])
            self.assertEqual("original_byte_equivalent", manifest["stage"])
            self.assertTrue(manifest["map_setting_override_installed"])
            self.assertFalse(manifest["unrelated_overrides_installed"])
            self.assertEqual(str(target), manifest["target_path_expected"])
            self.assertTrue((root / "evidence" / "q2e_a1_stage_manifest.json").is_file())
            config = json.loads((game_root / "config" / "game" / "mods.json").read_text(encoding="utf-8"))
            self.assertEqual(["tfm2_lol_map_spike"], config["enabled_mods"])

    def test_stage_b_requires_manifest_and_validates_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_root = self.make_game_root(temp_dir)
            original_path, source = self.write_q2e_pair(root)
            mutated = source.read_bytes()
            original_sha = install_runtime_spike_mod.sha256_file(original_path)
            output_sha = install_runtime_spike_mod.sha256_file(source)
            manifest_path = root / "evidence" / "mutation_manifest.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(
                json.dumps(
                    {
                        "input_path": str(original_path),
                        "input_sha256": original_sha,
                        "output_sha256": output_sha,
                        "input_size": original_path.stat().st_size,
                        "output_size": source.stat().st_size,
                        "changed_offsets": [427536, 427573],
                        "expected_changed_offsets": [427536, 427573],
                        "changed_cells": install_runtime_mutation_probe.EXPECTED_MUTATION_CELLS,
                        "changed_byte_count": 2,
                        "changed_cell_count": 2,
                        "transpose_mismatch_after": 0,
                        "runtime_installed": False,
                        "map_setting_node_world_transform": "unproven",
                    }
                ),
                encoding="utf-8",
            )
            old_baseline = install_runtime_mutation_probe.BASELINE_SHA256
            install_runtime_mutation_probe.BASELINE_SHA256 = original_sha
            try:
                manifest = install_runtime_mutation_probe.stage_runtime_mutation_probe(
                    game_root=game_root,
                    mode="B",
                    map_setting_source=source,
                    evidence_dir=root / "evidence",
                    mutation_manifest_path=manifest_path,
                    clean=True,
                    enable_exclusive=False,
                )
            finally:
                install_runtime_mutation_probe.BASELINE_SHA256 = old_baseline

            target = game_root / "mods" / "tfm2_lol_map_spike" / "setting" / "map_setting.map_setting"
            self.assertEqual(mutated, target.read_bytes())
            self.assertEqual("risk_accepted_two_byte_mutation", manifest["stage"])
            self.assertEqual(output_sha, manifest["mutation_manifest_output_sha256"])
            self.assertEqual([427536, 427573], manifest["approved_changed_offsets"])
            self.assertTrue((root / "evidence" / "q2e_b_stage_manifest.json").is_file())

    def test_stage_b_rejects_bad_mutation_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_root = self.make_game_root(temp_dir)
            original, source = self.write_q2e_pair(root)
            manifest_path = root / "evidence" / "mutation_manifest.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(
                json.dumps(
                    {
                        "input_path": str(original),
                        "input_sha256": install_runtime_spike_mod.sha256_file(original),
                        "output_sha256": install_runtime_spike_mod.sha256_file(source),
                        "input_size": original.stat().st_size,
                        "output_size": source.stat().st_size,
                        "changed_offsets": [1, 2],
                        "expected_changed_offsets": [427536, 427573],
                        "changed_cells": install_runtime_mutation_probe.EXPECTED_MUTATION_CELLS,
                        "changed_byte_count": 2,
                        "changed_cell_count": 2,
                        "transpose_mismatch_after": 0,
                        "runtime_installed": False,
                        "map_setting_node_world_transform": "unproven",
                    }
                ),
                encoding="utf-8",
            )
            old_baseline = install_runtime_mutation_probe.BASELINE_SHA256
            install_runtime_mutation_probe.BASELINE_SHA256 = install_runtime_spike_mod.sha256_file(original)
            try:
                with self.assertRaises(SystemExit) as raised:
                    install_runtime_mutation_probe.stage_runtime_mutation_probe(
                        game_root=game_root,
                        mode="B",
                        map_setting_source=source,
                        evidence_dir=root / "evidence",
                        mutation_manifest_path=manifest_path,
                        clean=True,
                    )
            finally:
                install_runtime_mutation_probe.BASELINE_SHA256 = old_baseline

            self.assertIn("changed_offsets", str(raised.exception))
            self.assertFalse((game_root / "mods" / "tfm2_lol_map_spike").exists())

    def test_stage_b_rejects_actual_diff_outside_approved_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_root = self.make_game_root(temp_dir)
            original, source = self.write_q2e_pair(root)
            mutated = bytearray(source.read_bytes())
            mutated[10] = 7
            source.write_bytes(mutated)
            manifest_path = root / "evidence" / "mutation_manifest.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(
                json.dumps(
                    {
                        "input_path": str(original),
                        "input_sha256": install_runtime_spike_mod.sha256_file(original),
                        "output_sha256": install_runtime_spike_mod.sha256_file(source),
                        "input_size": original.stat().st_size,
                        "output_size": source.stat().st_size,
                        "changed_offsets": [427536, 427573],
                        "expected_changed_offsets": [427536, 427573],
                        "changed_cells": install_runtime_mutation_probe.EXPECTED_MUTATION_CELLS,
                        "changed_byte_count": 2,
                        "changed_cell_count": 2,
                        "transpose_mismatch_after": 0,
                        "runtime_installed": False,
                        "map_setting_node_world_transform": "unproven",
                    }
                ),
                encoding="utf-8",
            )
            old_baseline = install_runtime_mutation_probe.BASELINE_SHA256
            install_runtime_mutation_probe.BASELINE_SHA256 = install_runtime_spike_mod.sha256_file(original)
            try:
                with self.assertRaises(SystemExit) as raised:
                    install_runtime_mutation_probe.stage_runtime_mutation_probe(
                        game_root=game_root,
                        mode="B",
                        map_setting_source=source,
                        evidence_dir=root / "evidence",
                        mutation_manifest_path=manifest_path,
                        clean=True,
                    )
            finally:
                install_runtime_mutation_probe.BASELINE_SHA256 = old_baseline

            self.assertIn("actual byte diff", str(raised.exception))
            self.assertFalse((game_root / "mods" / "tfm2_lol_map_spike").exists())

    def test_non_clean_existing_map_setting_override_fails_before_replacing_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_root = self.make_game_root(temp_dir)
            installed_mod = game_root / "mods" / "tfm2_lol_map_spike"
            installed_target = installed_mod / "setting" / "map_setting.map_setting"
            installed_target.parent.mkdir(parents=True)
            installed_target.write_bytes(b"old staged file")
            installed_override = {
                "asset/base/aseprite_resources/ingame/5v5/background_5v5": {
                    "remapping": "asset/tfm2_lol_map_spike/aseprite_resources/ingame/5v5/background_5v5",
                    "type": "override",
                },
                "asset/base/setting/map_setting": {
                    "remapping": "asset/tfm2_lol_map_spike/setting/map_setting",
                    "type": "override",
                },
            }
            (installed_mod / "mod.override_info").write_text(
                json.dumps(installed_override, indent=2) + "\n",
                encoding="utf-8",
            )
            original, source = self.write_q2e_pair(root)
            manifest_path = root / "evidence" / "mutation_manifest.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(
                json.dumps(
                    {
                        "input_path": str(original),
                        "input_sha256": install_runtime_spike_mod.sha256_file(original),
                        "output_sha256": install_runtime_spike_mod.sha256_file(source),
                        "input_size": original.stat().st_size,
                        "output_size": source.stat().st_size,
                        "changed_offsets": [427536, 427573],
                        "expected_changed_offsets": [427536, 427573],
                        "changed_cells": install_runtime_mutation_probe.EXPECTED_MUTATION_CELLS,
                        "changed_byte_count": 2,
                        "changed_cell_count": 2,
                        "transpose_mismatch_after": 0,
                        "runtime_installed": False,
                        "map_setting_node_world_transform": "unproven",
                    }
                ),
                encoding="utf-8",
            )
            old_baseline = install_runtime_mutation_probe.BASELINE_SHA256
            install_runtime_mutation_probe.BASELINE_SHA256 = install_runtime_spike_mod.sha256_file(original)
            try:
                with self.assertRaises(SystemExit) as raised:
                    install_runtime_mutation_probe.stage_runtime_mutation_probe(
                        game_root=game_root,
                        mode="B",
                        map_setting_source=source,
                        evidence_dir=root / "evidence",
                        mutation_manifest_path=manifest_path,
                        clean=False,
                    )
            finally:
                install_runtime_mutation_probe.BASELINE_SHA256 = old_baseline

            self.assertIn("already contains map_setting", str(raised.exception))
            self.assertEqual(b"old staged file", installed_target.read_bytes())
            self.assertEqual(installed_override, json.loads((installed_mod / "mod.override_info").read_text()))
            self.assertFalse((root / "evidence" / "q2e_b_stage_manifest.json").exists())

    def test_rejects_source_from_installed_mods_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game_root = self.make_game_root(temp_dir)
            source = game_root / "mods" / "tfm2_lol_map_spike" / "setting" / "map_setting.map_setting"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"installed")

            with self.assertRaises(SystemExit) as raised:
                install_runtime_mutation_probe.stage_runtime_mutation_probe(
                    game_root=game_root,
                    mode="A2",
                    map_setting_source=source,
                    evidence_dir=Path(temp_dir) / "evidence",
                )

            self.assertIn("installed mods tree", str(raised.exception))

    def test_mode_b_requires_mutation_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_root = self.make_game_root(temp_dir)
            source = self.write_source(root, "mutated.map_setting", b"mutated")

            with self.assertRaises(SystemExit) as raised:
                install_runtime_mutation_probe.stage_runtime_mutation_probe(
                    game_root=game_root,
                    mode="B",
                    map_setting_source=source,
                    evidence_dir=root / "evidence",
                )

            self.assertIn("requires --mutation-manifest", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
