from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import map_setting_inspect
from tools import map_setting_mutate_symmetric_edge as mutate_edge
from tools import map_setting_round_trip
from test_map_setting_round_trip import synthetic_map_setting


class MapSettingMutateSymmetricEdgeTests(unittest.TestCase):
    def synthetic_cells(self, data: bytes) -> tuple[mutate_edge.MutationCell, mutate_edge.MutationCell]:
        document = map_setting_round_trip.decode_map_setting(data)
        return (
            mutate_edge.MutationCell(
                logical_coordinate=(1, 0),
                source_node=0,
                target_node=1,
                offset=map_setting_inspect.chunked_cell_offset(document.chunked_binary_layer, 1, 0),
                old_value=1,
                new_value=0,
            ),
            mutate_edge.MutationCell(
                logical_coordinate=(0, 1),
                source_node=1,
                target_node=0,
                offset=map_setting_inspect.chunked_cell_offset(document.chunked_binary_layer, 0, 1),
                old_value=1,
                new_value=0,
            ),
        )

    def write_source(self, root: Path, data: bytes | None = None) -> Path:
        source = root / "source" / "map_setting.map_setting"
        source.parent.mkdir(parents=True)
        source.write_bytes(data if data is not None else synthetic_map_setting())
        return source

    def test_mutates_exact_two_symmetric_cells_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data = synthetic_map_setting()
            source = self.write_source(root, data)
            output = root / "evidence" / "mutated.map_setting"
            manifest_path = root / "evidence" / "mutation_manifest.json"
            cells = self.synthetic_cells(data)

            manifest = mutate_edge.mutate_symmetric_edge(
                input_path=source,
                output_path=output,
                manifest_path=manifest_path,
                confirm_risk_accepted=True,
                expected_sha256=map_setting_round_trip.sha256_bytes(data),
                cells=cells,
            )

            self.assertTrue(output.is_file())
            self.assertTrue(manifest_path.is_file())
            mutated = output.read_bytes()
            self.assertNotEqual(data, mutated)
            self.assertEqual([cell.offset for cell in cells], manifest["changed_offsets"])
            self.assertEqual(2, manifest["changed_cell_count"])
            self.assertEqual(2, manifest["changed_byte_count"])
            self.assertEqual(0, manifest["transpose_mismatch_before"])
            self.assertEqual(0, manifest["transpose_mismatch_after"])
            self.assertFalse(manifest["runtime_installed"])
            self.assertEqual("unproven", manifest["map_setting_node_world_transform"])
            self.assertEqual(data, source.read_bytes())
            written_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["output_sha256"], written_manifest["output_sha256"])
            map_setting_round_trip.decode_map_setting(mutated)

    def test_refuses_without_explicit_risk_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data = synthetic_map_setting()
            source = self.write_source(root, data)
            output = root / "evidence" / "mutated.map_setting"
            manifest_path = root / "evidence" / "mutation_manifest.json"

            with self.assertRaises(SystemExit) as raised:
                mutate_edge.mutate_symmetric_edge(
                    input_path=source,
                    output_path=output,
                    manifest_path=manifest_path,
                    confirm_risk_accepted=False,
                    expected_sha256=map_setting_round_trip.sha256_bytes(data),
                    cells=self.synthetic_cells(data),
                )

            self.assertIn("confirm-risk-accepted", str(raised.exception))
            self.assertFalse(output.exists())
            self.assertFalse(manifest_path.exists())

    def test_refuses_sha_mismatch_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data = synthetic_map_setting()
            source = self.write_source(root, data)
            output = root / "evidence" / "mutated.map_setting"
            manifest_path = root / "evidence" / "mutation_manifest.json"

            with self.assertRaises(SystemExit) as raised:
                mutate_edge.mutate_symmetric_edge(
                    input_path=source,
                    output_path=output,
                    manifest_path=manifest_path,
                    confirm_risk_accepted=True,
                    expected_sha256="0" * 64,
                    cells=self.synthetic_cells(data),
                )

            self.assertIn("does not match expected", str(raised.exception))
            self.assertFalse(output.exists())
            self.assertFalse(manifest_path.exists())
            self.assertEqual(data, source.read_bytes())

    def test_refuses_old_value_mismatch_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data = bytearray(synthetic_map_setting())
            cells = self.synthetic_cells(bytes(data))
            data[cells[0].offset] = 0
            data[cells[1].offset] = 0
            source = self.write_source(root, bytes(data))
            output = root / "evidence" / "mutated.map_setting"
            manifest_path = root / "evidence" / "mutation_manifest.json"

            with self.assertRaises(SystemExit) as raised:
                mutate_edge.mutate_symmetric_edge(
                    input_path=source,
                    output_path=output,
                    manifest_path=manifest_path,
                    confirm_risk_accepted=True,
                    expected_sha256=map_setting_round_trip.sha256_bytes(bytes(data)),
                    cells=cells,
                )

            self.assertIn("expected old value", str(raised.exception))
            self.assertFalse(output.exists())
            self.assertFalse(manifest_path.exists())
            self.assertEqual(bytes(data), source.read_bytes())

    def test_refuses_repository_internal_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data = synthetic_map_setting()
            source = self.write_source(root, data)

            with self.assertRaises(SystemExit) as raised:
                mutate_edge.mutate_symmetric_edge(
                    input_path=source,
                    output_path=map_setting_round_trip.REPO_ROOT / "tmp_mutated.map_setting",
                    manifest_path=root / "manifest.json",
                    confirm_risk_accepted=True,
                    expected_sha256=map_setting_round_trip.sha256_bytes(data),
                    cells=self.synthetic_cells(data),
                )

            self.assertIn("repository-internal output", str(raised.exception))
            self.assertEqual(data, source.read_bytes())

    def test_refuses_output_input_hardlink_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data = synthetic_map_setting()
            source = self.write_source(root, data)
            output = root / "evidence" / "mutated.map_setting"
            output.parent.mkdir()
            try:
                os.link(source, output)
            except OSError as exc:
                self.skipTest(f"hardlinks are not available in this environment: {exc}")

            with self.assertRaises(SystemExit) as raised:
                mutate_edge.mutate_symmetric_edge(
                    input_path=source,
                    output_path=output,
                    manifest_path=root / "evidence" / "manifest.json",
                    confirm_risk_accepted=True,
                    expected_sha256=map_setting_round_trip.sha256_bytes(data),
                    cells=self.synthetic_cells(data),
                )

            self.assertIn("Input, output, and manifest paths must be distinct", str(raised.exception))
            self.assertEqual(data, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
