from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import map_setting_inspect
from tools import map_setting_round_trip as round_trip
from test_map_setting_round_trip import synthetic_map_setting


class MapSettingInspectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = synthetic_map_setting()
        self.document = round_trip.decode_map_setting(self.data)

    def test_flatten_chunked_binary_layer(self) -> None:
        values, width, height = map_setting_inspect.flatten_chunked_binary_layer(self.document.chunked_binary_layer)

        self.assertEqual((4, 4), (width, height))
        self.assertEqual(16, len(values))
        self.assertEqual({"0": 8, "1": 8}, map_setting_inspect.histogram(values))
        self.assertEqual(
            {
                "0": {"count": 8, "bbox": [0, 0, 3, 3]},
                "1": {"count": 8, "bbox": [0, 0, 3, 3]},
            },
            map_setting_inspect.bounding_boxes_by_value(values, width, height),
        )

    def test_unpack_packed4_layer(self) -> None:
        values = map_setting_inspect.unpack_packed4_layer(self.document.packed4_layers[0])

        self.assertEqual(list(range(16)), values)

    def test_symmetry_counters(self) -> None:
        symmetric = [
            1,
            2,
            3,
            4,
            2,
            5,
            6,
            7,
            3,
            6,
            5,
            8,
            4,
            7,
            8,
            1,
        ]

        self.assertEqual(0, map_setting_inspect.matrix_transpose_mismatch_count(symmetric, 4))
        self.assertGreater(map_setting_inspect.rotational_symmetry_mismatch_count(symmetric, 4, 4), 0)

    def test_packed4_cell_location_reports_byte_and_nibble(self) -> None:
        layer = self.document.packed4_layers[0]

        low = map_setting_inspect.packed4_cell_location(layer, 0, 0, 4)
        high = map_setting_inspect.packed4_cell_location(layer, 1, 0, 4)

        self.assertEqual(layer.offset + 16, low["serialized_byte_offset"])
        self.assertEqual("low", low["nibble"])
        self.assertEqual(layer.offset + 16, high["serialized_byte_offset"])
        self.assertEqual("high", high["nibble"])

    def test_inspect_rejects_repository_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "map_setting"
            source.write_bytes(self.data)

            with self.assertRaises(SystemExit) as raised:
                map_setting_inspect.inspect_map_setting(
                    input_path=source,
                    output_dir=round_trip.REPO_ROOT / "tmp_layer_inspection",
                    expected_sha256=round_trip.sha256_file(source),
                )

            self.assertIn("repository-internal output directory", str(raised.exception))

    def test_inspect_rejects_repository_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(SystemExit) as raised:
                map_setting_inspect.inspect_map_setting(
                    input_path=round_trip.REPO_ROOT / "README.md",
                    output_dir=Path(temp_dir) / "inspection",
                    expected_sha256=None,
                )

            self.assertIn("repository-internal input", str(raised.exception))

    def test_read_bundle_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle = Path(temp_dir) / "bundle.game_data"
            asset_type = b"png"
            asset_key = b"asset/test/key"
            payload = b"payload"
            bundle.write_bytes(
                (1).to_bytes(4, "little")
                + len(asset_type).to_bytes(4, "little")
                + asset_type
                + len(asset_key).to_bytes(4, "little")
                + asset_key
                + len(payload).to_bytes(4, "little")
                + payload
            )

            found_type, found_payload = map_setting_inspect.read_bundle_entry(bundle, "asset/test/key")

            self.assertEqual("png", found_type)
            self.assertEqual(payload, found_payload)

    def test_stdout_summary_omits_large_histograms(self) -> None:
        manifest = {
            "probe": "map_setting_layer_inspection",
            "input_sha256": "abc",
            "output_dir": "D:\\evidence",
            "layers": {
                "chunked_binary": {"shape": [900, 900], "histogram": {"0": 1}},
                "packed4_0": {"shape": [900, 900], "histogram": {"15": 1}},
                "packed4_1": {"value_count": 27000, "histogram": {"0": 1}},
            },
            "candidate_mutation": {
                "status": "selected_for_follow_up_review",
                "layer": "chunked_binary",
                "logical_coordinate": [32, 31],
            },
            "safety": {"read_only": True},
        }

        summary = map_setting_inspect.stdout_summary(manifest)

        self.assertNotIn("histogram", summary)
        self.assertEqual("selected_for_follow_up_review", summary["candidate_status"])
        self.assertTrue(summary["read_only"])


if __name__ == "__main__":
    unittest.main()
